import asyncio
from collections import deque
from bleak import BleakClient, BleakScanner

HR_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
HAMMERHEAD_MAC_ADDRESS = "C6:3E:75:B3:A5:EB"

async def discover_and_connect_ble_device():
    print("🔍 Meklēju BLE ierīces...")
    devices = await BleakScanner.discover(timeout=5.0)
    
    target_device = None
    for device in devices:
        if device.name and ("Polar H10" in device.name or "19BE12139" in device.name):
            print(f"✅ Atrasta Polar H10 ierīce: {device.name} ({device.address})")
            target_device = device
            break
        elif device.address == HAMMERHEAD_MAC_ADDRESS:
            print(f"✅ Atrasta Hammerhead ierīce: {device.name} ({device.address})")
            target_device = device
            break
            
    if not target_device:
        print("❌ Neizdevās atrast sirds ritma jostu. Pārbaudi savienojumu vai samitrini kontaktus.")
        return None
        
    return target_device

async def ble_receiver(shared_freq, shared_tempo, classifier, ai_agent, calculate_rmssd):
    import datetime
    from core.data_logger import log_q_agent_interaction, log_session_summary

    rr_history = []
    last_rmssd = 0
    decision_counter = 0
    last_epoch_rmssd = None
    session_rmssd_history = []
    start_time = datetime.datetime.now()
    rmssd_window = deque(maxlen=20)  # 20-beat sliding window
    last_smoothed_rmssd = None
    
    # Track previous state and action for Q-learning logging
    previous_hr = 0
    previous_rmssd = 0.0
    previous_smoothed_rmssd = 0.0
    previous_ai_state = 0
    previous_action_freq = 0.0

    def notification_handler(sender, data):
        # 1. RAW DEBUG PRINT (removed after debugging complete):
        # print(f"DEBUG PAKETE: {data.hex()}", flush=True)
        
        nonlocal last_rmssd, rr_history, decision_counter, rmssd_window, last_smoothed_rmssd
        nonlocal previous_hr, previous_rmssd, previous_smoothed_rmssd, previous_ai_state, previous_action_freq
        
        flags = data[0]
        hr_format = flags & 0x01
        current_offset = 1
        
        if hr_format == 0:
            hr = data[current_offset]; current_offset += 1
        else:
            hr = int.from_bytes(data[current_offset:current_offset+2], byteorder='little'); current_offset += 2

        rr_present = (flags & 0x10) >> 4
        if rr_present:
            while current_offset < len(data):
                rr_raw = int.from_bytes(data[current_offset:current_offset+2], byteorder='little')
                rr_history.append( int((rr_raw / 1024.0) * 1000.0) )
                if len(rr_history) > 20: rr_history.pop(0)
                current_offset += 2

        current_rmssd = calculate_rmssd(rr_history)
        
        reward = 0
        if current_rmssd > last_rmssd + 0.5: reward = 1.0   
        elif current_rmssd < last_rmssd - 0.5: reward = -1.0 
        ai_agent.update_q_table(reward)
        last_rmssd = current_rmssd

        if current_rmssd > 0:
            predicted_state = classifier.predict(hr, current_rmssd) 
        else:
            predicted_state = 0
            
        state_text = "STRESS" if predicted_state == 1 else "MIERS "

        decision_counter += 1
        
        # =========================================================
        # REĀLLAIKA DRUKA (DEMO REŽĪMS)
        # =========================================================
        rmssd_window.append(current_rmssd)
        smoothed_rmssd = sum(rmssd_window) / len(rmssd_window)

        trend_arrow = "➡️" # Default to no trend
        if last_smoothed_rmssd is not None:
            if smoothed_rmssd > last_smoothed_rmssd + 0.5:
                trend_arrow = "↗️" # Improving / Relaxing
            elif smoothed_rmssd < last_smoothed_rmssd - 0.5:
                trend_arrow = "↘️" # Decreasing / Stressing
        
        last_smoothed_rmssd = smoothed_rmssd

        print(f"Sitiens [{decision_counter:2d}/60] | BPM: {hr:3d} | RMSSD: {current_rmssd:5.1f}ms | Vid. Trend: {smoothed_rmssd:5.1f}ms {trend_arrow} | AI: {state_text}", flush=True)

        # =========================================================
        # Q-LEARNING EPOHA (DEMO REŽĪMS): Reizi 60 sitienos
        # =========================================================
        if decision_counter >= 60:
            nonlocal last_epoch_rmssd
   
            if last_epoch_rmssd is not None:
                delta = current_rmssd - last_epoch_rmssd
                trend_icon = "📈" if delta >= 0 else "📉"
                status_text = "UZLABOJAS (Parasimpātiskā atjaunošanās)" if delta > 0 else "PASLIKTINĀS (Pieaug stress)"
                print(f"{trend_icon} PROGRESA STATUSS: Tavs HRV (RMSSD) mainījās par {delta:+.1f} ms -> {status_text}", flush=True)
            
            last_epoch_rmssd = current_rmssd
            session_rmssd_history.append(current_rmssd)

            # Log the previous interaction before choosing a new action
            log_q_agent_interaction(
                datetime.datetime.now(),
                previous_hr,
                previous_rmssd,
                previous_smoothed_rmssd,
                previous_ai_state,
                previous_action_freq,
                reward, # The reward calculated in this epoch for the *previous* action
                current_rmssd # The new state (next_rmssd)
            )

            chosen_freq, tactic = ai_agent.choose_action(predicted_state)
            shared_freq.value = chosen_freq
            decision_counter = 0
            
            target_bpm = max(55, hr - 5)
            shared_tempo.value = target_bpm / 60.0 

            print("\n" + "═"*60, flush=True)
            print(f" 🤖 Q-AĢENTA LĒMUMS: Pārslēdzu uz {chosen_freq}Hz {tactic}", flush=True)
            print("═"*60 + "\n", flush=True)
            
            # Update previous state and action for the next logging cycle
            previous_hr = hr
            previous_rmssd = current_rmssd
            previous_smoothed_rmssd = smoothed_rmssd
            previous_ai_state = predicted_state
            previous_action_freq = chosen_freq

    device = await discover_and_connect_ble_device()
    if not device: 
        return

    try:
        # For Windows: Force no-pairing mode if the device supports it
        async with BleakClient(device, timeout=10.0, winrt={"use_cached_services": False}) as client:
            print("✅ Savienots ar ierīci! Sāku saņemt datus...", flush=True)
            
            # Subscribe to the heart rate characteristic
            await client.start_notify(HR_MEASUREMENT_UUID, notification_handler)
            
            # Keep the connection alive (e.g., for 1 hour)
            await asyncio.sleep(3600)
            
            await client.stop_notify(HR_MEASUREMENT_UUID)
    except Exception as e:
        print(f"Savienojuma kļūda: {repr(e)}")
    finally:
        end_time = datetime.datetime.now()
        session_duration = end_time - start_time
        minutes, seconds = divmod(session_duration.total_seconds(), 60)

        if len(session_rmssd_history) > 0:
            baseline_rmssd = sum(session_rmssd_history[:3]) / min(3, len(session_rmssd_history))
            final_rmssd = sum(session_rmssd_history[-3:]) / min(3, len(session_rmssd_history))
            total_delta = final_rmssd - baseline_rmssd

            print("\n" + "═"*60)
            print("📊 SESIJAS KOPSAVILKUMS (SESSION SUMMARY)")
            print("═"*60)
            print(f"⏳ Kopējais laiks: {int(minutes)} min {int(seconds)} sek")
            print(f"🏁 Sākuma bāzes RMSSD (Pirmās minūtes): {baseline_rmssd:.1f} ms")
            print(f"🎯 Beigu RMSSD (Pēdējās minūtes): {final_rmssd:.1f} ms")
            print(f"📈 KOPĒJAIS UZLABOJUMS (DELTA): {total_delta:+.1f} ms")
            print("═"*60 + "\n")

            log_session_summary(start_time.date(), session_duration.total_seconds(), baseline_rmssd, final_rmssd, total_delta)
