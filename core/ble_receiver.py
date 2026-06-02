import asyncio
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
    rr_history = []
    last_rmssd = 0
    decision_counter = 0

    def notification_handler(sender, data):
        nonlocal last_rmssd, rr_history, decision_counter
        
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
        
        print(f"Sitiens [{decision_counter:2d}/60] | BPM: {hr:3d} | RMSSD: {current_rmssd:5.1f}ms | AI klasifikators: {state_text}")

        if decision_counter >= 60:
            chosen_freq, tactic = ai_agent.choose_action(predicted_state)
            shared_freq.value = chosen_freq
            decision_counter = 0
            
            target_bpm = max(55, hr - 5)
            shared_tempo.value = target_bpm / 60.0 

            print("\n" + "═"*60)
            print(f" 🤖 Q-AĢENTA LĒMUMS: Pārslēdzu uz {chosen_freq}Hz {tactic}")
            print("═"*60 + "\n")

    device = await discover_and_connect_ble_device()
    if not device: 
        return

    try:
        async with BleakClient(device, timeout=15.0) as client:
            print("\n🚀 HIBRĪDA SISTĒMA ONLINE: Datu plūsma sākta!")
            await client.start_notify(HR_MEASUREMENT_UUID, notification_handler)
            await asyncio.sleep(3600)
    except Exception as e:
        print(f"Savienojuma kļūda: {repr(e)}")