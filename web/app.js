const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const state={view:"home",sessionId:null,running:false,remaining:360,baselineHrv:null,muted:false,connected:false,connectionMode:"none",bluetoothDevice:null,heartCharacteristic:null,rrHistory:[],lastBioUpload:0,selectedDevice:"Polar H10",mood:"steady",recommendedDuration:360,audioBpm:64,history:[],audio:null};
let suppressDeviceClickUntil=0;
const INTERRUPTED_SESSION_KEY="nevori_interrupted_session";
const SETTINGS_KEY="nevori_settings";

function toast(message){const el=$("#toast");el.textContent=message;el.classList.add("show");clearTimeout(toast.timer);toast.timer=setTimeout(()=>el.classList.remove("show"),2300)}
function commitView(view){
  state.view=view;
  if(view==="home")applySettings();
  $$(".view").forEach(v=>v.classList.toggle("active",v.id===`${view}-view`));
  document.body.classList.toggle("session-active",view==="session");
  document.body.classList.toggle("focused-flow",view!=="home");
  window.scrollTo({top:0,behavior:"instant"});
}
function show(view){
  if(view===state.view)return;
  if(document.startViewTransition&&!window.matchMedia("(prefers-reduced-motion: reduce)").matches){
    document.startViewTransition(()=>commitView(view));
  }else{
    document.body.classList.add("view-changing");
    setTimeout(()=>{commitView(view);requestAnimationFrame(()=>document.body.classList.remove("view-changing"))},140);
  }
}
function formatTime(seconds){return`${Math.floor(seconds/60).toString().padStart(2,"0")}:${(seconds%60).toString().padStart(2,"0")}`}
function readSettings(){
  try{return {...{name:"Māris",photo:"",duration:360,volume:16,reminders:true,reduceMotion:false},...JSON.parse(localStorage.getItem(SETTINGS_KEY)||"{}")}}catch{return{name:"Māris",photo:"",duration:360,volume:16,reminders:true,reduceMotion:false}}
}
function getInitials(name){
  const parts=name.trim().split(/\s+/).filter(Boolean);
  return (parts.length>1?parts[0][0]+parts.at(-1)[0]:(parts[0]||"N").slice(0,2)).toLocaleUpperCase();
}
function greetingForHour(hour){
  if(hour>=5&&hour<12)return"Good morning";
  if(hour>=12&&hour<17)return"Good afternoon";
  if(hour>=17&&hour<22)return"Good evening";
  return"Good night";
}
function updateHomeTime(date=new Date()){
  const settings=readSettings();
  $("#home-title").textContent=`${greetingForHour(date.getHours())}, ${settings.name}.`;
  $("#home-date").textContent=new Intl.DateTimeFormat(undefined,{weekday:"long",month:"long",day:"numeric"}).format(date);
  $("#mobile-clock").textContent=date.toLocaleTimeString([],{hour:"2-digit",minute:"2-digit",hour12:false});
}
function applyAvatar(name,photo){
  $$(".profile-avatar").forEach(avatar=>{
    avatar.querySelector(".avatar-initials").textContent=getInitials(name);
    avatar.classList.toggle("has-photo",Boolean(photo));
    avatar.style.backgroundImage=photo?`url("${photo}")`:"";
  });
  $("#remove-profile-photo").hidden=!photo;
}
function applySettings(){
  const settings=readSettings();
  updateHomeTime();
  document.body.classList.toggle("user-reduced-motion",settings.reduceMotion);
  $(".next-panel").hidden=!settings.reminders;
  applyAvatar(settings.name,settings.photo);
}
function populateSettings(){
  const settings=readSettings();
  $("#setting-name").value=settings.name;
  $("#setting-duration").value=String(settings.duration);
  $("#setting-volume").value=String(settings.volume);
  $("#setting-volume-value").textContent=`${settings.volume}%`;
  $("#setting-reminders").checked=settings.reminders;
  $("#setting-motion").checked=settings.reduceMotion;
  applyAvatar(settings.name,settings.photo);
}
function applyLocalTimeTheme(date=new Date()){
  const hour=date.getHours(),isDay=hour>=6&&hour<18,button=$("#start-flow");
  button.classList.toggle("time-day",isDay);button.classList.toggle("time-night",!isDay);
  $("#session-time-label").textContent=isDay?"DAYTIME RESET":"EVENING UNWIND";
  $("#session-button-copy").textContent=isDay?"Begin daytime session":"Begin evening session";
  updateHomeTime(date);
  $("#home-recovery-copy").textContent=hour>=18||hour<6?"Recovery looks promising tonight.":"Recovery looks promising today.";
}
function readInterruptedSession(){
  try{return JSON.parse(localStorage.getItem(INTERRUPTED_SESSION_KEY)||"null")}catch{return null}
}
function saveInterruptedSession(){
  if(!state.sessionId||state.remaining<=0)return;
  localStorage.setItem(INTERRUPTED_SESSION_KEY,JSON.stringify({
    sessionId:state.sessionId,
    remaining:state.remaining,
    baselineHrv:state.baselineHrv,
    selectedDevice:state.selectedDevice,
    savedAt:Date.now()
  }));
  renderInterruptedSession();
}
function clearInterruptedSession(){
  localStorage.removeItem(INTERRUPTED_SESSION_KEY);
  renderInterruptedSession();
}
function renderInterruptedSession(){
  const saved=readInterruptedSession(),button=$("#resume-session");
  button.hidden=!saved;
  if(saved)$("#resume-session-copy").textContent=`${formatTime(saved.remaining)} remaining · ${saved.selectedDevice||"saved device"}`;
}
function resumeInterruptedSession(){
  const saved=readInterruptedSession();
  if(!saved)return;
  state.sessionId=saved.sessionId;
  state.remaining=saved.remaining;
  state.baselineHrv=saved.baselineHrv;
  state.selectedDevice=saved.selectedDevice||state.selectedDevice;
  $("#player-time").textContent=formatTime(state.remaining);
  $("#live-device-name").textContent=`${state.selectedDevice} · signal good`;
  show("session");ensureAudio();
  state.running=true;$("#session-view").classList.add("running");$("#orb-label").textContent="listening";setAudioVolume(true);
  toast("Continuing where you left off");
}
function beginNewSessionFlow(){
  const duration=state.recommendedDuration||readSettings().duration;
  state.sessionId=null;
  state.remaining=duration;
  state.baselineHrv=null;
  $("#player-time").textContent=formatTime(duration);
  if(state.connectionMode==="bluetooth"&&state.bluetoothDevice?.gatt?.connected)openMoodScreen();
  else if(state.connectionMode==="demo")openMoodScreen();
  else show("connect");
}
function renderWave(){const points=Array.from({length:50},(_,i)=>{const x=i*600/49,y=50+Math.sin(i*.72+Date.now()/420)*18+Math.sin(i*1.7)*6;return`${i?"L":"M"}${x.toFixed(1)},${y.toFixed(1)}`}).join(" ");$("#live-wave-path").setAttribute("d",points)}
function buildChart(days){const chart=$("#week-chart");chart.innerHTML="";days.forEach((day,i)=>{const el=document.createElement("div");el.className=`bar-day ${i===days.length-1?"active":""}`;el.innerHTML=`<i style="height:${Math.max(8,day.shift*7)}px"></i><span>${day.day}</span>`;chart.appendChild(el)})}
function buildSessions(sessions){
  $("#session-list").innerHTML=sessions.length?sessions.slice(0,3).map(s=>`<div class="session-row"><div class="session-date"><strong>${s.date}</strong><small>${s.month}</small></div><div class="session-info"><strong>${s.title}</strong><span>${s.duration} min · ${s.audio}</span></div><span class="session-shift">${s.shift>=0?"+":""}${s.shift.toFixed(1)} ms</span><span class="session-arrow">→</span></div>`).join(""):`<div class="empty-sessions"><strong>Your sessions will appear here</strong><span>Finish a recharge to begin your local recovery history.</span></div>`;
}
async function loadDashboard(){
  try{
    const user=encodeURIComponent(readSettings().name),response=await fetch(`/api/dashboard?user=${user}`),data=await response.json();
    buildChart(data.week);buildSessions(data.sessions);
    $("#week-average").textContent=`${data.average_shift>=0?"+":""}${data.average_shift.toFixed(1)}`;
    $("#weekly-sessions").textContent=data.weekly_sessions;$("#weekly-minutes").textContent=data.weekly_minutes;
    $("#learning-percent").textContent=`${data.learning.percent}%`;
    $("#learning-sessions").textContent=data.learning.sessions_observed;
    $("#learning-patterns").textContent=data.learning.patterns_tested;
    $("#learning-consistency").textContent=`${data.learning.response_consistency}%`;
    $("#learning-confidence").textContent=data.learning.confidence;
    $("#readiness-label").textContent=data.today.readiness;
    $("#readiness-score").textContent=data.today.live_data?data.today.capacity:"--";
    $("#readiness-metric").textContent=data.today.live_data?`HRV ${data.today.current_rmssd} ms · baseline ${data.today.baseline_rmssd} ms`:"Connect a wearable to calculate from live HRV";
    $("#home-recommendation").textContent=`${data.today.recommendation} · ${data.today.recommended_minutes} min`;
    $("#recommendation-why").textContent=data.today.why;
    $("#weekly-goal").textContent=data.goal.remaining?`${data.goal.completed} of ${data.goal.target} sessions`:"Weekly goal complete";
    $("#personal-insight").textContent=data.insight;
    $("#nudge-duration").textContent=`${String(data.today.recommended_minutes).padStart(2,"0")}:00`;
    state.recommendedDuration=data.today.recommended_minutes*60;
    state.mood=data.today.mood;
    $$(".mood-options button").forEach(button=>button.classList.toggle("selected",button.dataset.mood===state.mood));
    $("#checkin-status").textContent=({drained:"Feeling low",stretched:"Feeling tense",steady:"Feeling okay",bright:"Feeling good"})[state.mood]||"Help Nevori choose";
    $(".learning-note strong").textContent=data.learning.sessions_observed?`${data.learning.best_frequency} Hz · adaptive personal pulse`:"Waiting for your first completed session";
    $(".learning-note p").textContent=data.learning.sessions_observed?"Nevori is comparing which audio pattern produces the most consistent positive HRV response.":"Your completed sessions will teach the local model which audio patterns work best for you.";
    $("#strongest-response").innerHTML=data.best_session?`Your strongest recorded shift is <strong>${data.best_session.shift>=0?"+":""}${data.best_session.shift} ms</strong> after ${data.best_session.duration} minutes.`:"Complete your first session to begin building a personal recovery pattern.";
  }catch{buildChart(["S","M","T","W","T","F","S"].map(day=>({day,shift:0})));buildSessions([])}
}
async function fetchState(){
  if(state.view!=="session")return;
  try{
    const r=await fetch("/api/state"),d=await r.json();
    $("#heart-rate").textContent=Math.round(d.heart_rate);$("#rmssd").textContent=Math.round(d.rmssd);
    if(state.running&&state.baselineHrv){
      const delta=d.rmssd-state.baselineHrv;
      $("#session-shift").textContent=`${delta>=0?"+":""}${delta.toFixed(1)} ms`;
      state.audioBpm=d.audio_bpm||state.audioBpm;
      $("#audio-bpm").textContent=Math.round(state.audioBpm);
      $("#adaptation-copy").textContent=d.adaptation_copy;
      $("#ai-state").textContent=d.ai_mode;
      $("#science-note").textContent=`Nevori's local model selected a ${d.audio_frequency} Hz pattern from your live HRV response.`;
      if(state.audio)state.audio.lfo.frequency.setTargetAtTime(state.audioBpm/60,state.audio.ctx.currentTime,2);
    }
  }catch{}
}

function ensureAudio(){
  if(state.audio)return;
  const AudioCtx=window.AudioContext||window.webkitAudioContext;
  if(!AudioCtx)return;
  const ctx=new AudioCtx(),master=ctx.createGain(),filter=ctx.createBiquadFilter(),carrier=ctx.createOscillator(),pulse=ctx.createGain(),lfo=ctx.createOscillator(),depth=ctx.createGain();
  carrier.type="sine";carrier.frequency.value=110;filter.type="lowpass";filter.frequency.value=420;master.gain.value=.0001;lfo.type="sine";lfo.frequency.value=state.audioBpm/60;depth.gain.value=.16;pulse.gain.value=.32;
  lfo.connect(depth);depth.connect(pulse.gain);carrier.connect(filter);filter.connect(pulse);pulse.connect(master);master.connect(ctx.destination);carrier.start();lfo.start();
  state.audio={ctx,master,lfo,carrier};
}
function setAudioVolume(on){if(!state.audio)return;const volume=readSettings().volume/100;state.audio.master.gain.cancelScheduledValues(state.audio.ctx.currentTime);state.audio.master.gain.linearRampToValueAtTime(on&&!state.muted?volume:.0001,state.audio.ctx.currentTime+.8)}
function adaptAudio(bio,delta){
  let target=64,label="Holding a steady 64 BPM pulse",science="The pulse is holding while Nevori checks whether your HRV response is stable.",ai="Calibrating";
  if(delta>5){target=56;label="Your HRV is rising — easing the pulse to 56 BPM";science="A positive RMSSD trend triggered a gradual tempo reduction.";ai="Responding well"}
  else if(delta>1.5){target=60;label="A gentle shift appeared — slowing to 60 BPM";science="The sound changed after a sustained positive HRV trend.";ai="Adapting"}
  else if(state.remaining<300){target=62;label="Keeping the tone warm and reducing to 62 BPM";ai="Testing response"}
  state.audioBpm+=(target-state.audioBpm)*.08;$("#audio-bpm").textContent=Math.round(state.audioBpm);$("#adaptation-copy").textContent=label;$("#science-note").textContent=science;$("#ai-state").textContent=ai;
  if(state.audio)state.audio.lfo.frequency.setTargetAtTime(state.audioBpm/60,state.audio.ctx.currentTime,2);
}
function selectDevice(button){
  if(state.bluetoothDevice?.gatt?.connected)state.bluetoothDevice.gatt.disconnect();
  state.bluetoothDevice=null;
  state.selectedDevice=button.dataset.device;
  state.connected=false;
  state.connectionMode="none";
  updateHomeDeviceState();
  $$(".device-option").forEach(option=>{const selected=option===button;option.classList.toggle("selected",selected);option.setAttribute("aria-selected",selected)});
  button.scrollIntoView({behavior:"smooth",block:"nearest",inline:"center"});
  $(".device-status").classList.remove("connected","demo","error","scanning");
  $(".status-check").textContent="○";
  $("#connection-label").textContent="READY TO CONNECT";
  $("#connection-name").textContent=`${state.selectedDevice} selected`;
  $("#signal-copy").textContent="Waiting for signal";
  const connectButton=$("#connect-device");connectButton.textContent="Connect my device";connectButton.onclick=()=>connect(false);
  const index=$$(".device-option").indexOf(button);
  $("#mobile-device-count").textContent=`${index+1} of 7`;
}
async function connect(useDemo=false){
  const button=$("#connect-device"),status=$(".device-status");
  state.connected=false;
  status.classList.remove("connected","demo","error");
  if(useDemo){
    state.connectionMode="demo";
    updateHomeDeviceState();
    status.classList.add("demo");
    $(".status-check").textContent="◌";
    $("#connection-label").textContent="DEMO MODE";
    $("#connection-name").textContent="Simulated bio signal";
    $("#signal-copy").textContent="No physical device connected";
    $("#live-device-name").textContent="Demo signal · simulated";
    button.textContent="Continue";
    button.onclick=()=>openMoodScreen();
    toast("Demo signal selected");
    return;
  }
  status.classList.add("scanning");
  $(".status-check").textContent="…";
  button.textContent="Choose Bluetooth device";
  $("#connection-label").textContent="WAITING FOR BLUETOOTH";
  $("#signal-copy").textContent="Select your device in the browser prompt";
  try{
    if(!navigator.bluetooth)throw new Error("Bluetooth is not supported in this browser");
    const device=await navigator.bluetooth.requestDevice({acceptAllDevices:true,optionalServices:["heart_rate"]});
    const server=await device.gatt.connect();
    const heartService=await server.getPrimaryService("heart_rate");
    const characteristic=await heartService.getCharacteristic("heart_rate_measurement");
    await characteristic.startNotifications();
    characteristic.addEventListener("characteristicvaluechanged",handleHeartMeasurement);
    state.heartCharacteristic=characteristic;
    state.bluetoothDevice=device;
    state.connected=true;
    state.connectionMode="bluetooth";
    updateHomeDeviceState();
    status.classList.remove("scanning");
    status.classList.add("connected");
    $(".status-check").textContent="✓";
    $("#connection-label").textContent="CONNECTED";
    $("#connection-name").textContent=device.name||state.selectedDevice;
    $("#signal-copy").textContent="Heart-rate service available";
    $("#live-device-name").textContent=`${device.name||state.selectedDevice} · connected`;
    device.addEventListener("gattserverdisconnected",()=>{
      state.connected=false;state.connectionMode="none";state.bluetoothDevice=null;updateHomeDeviceState();
      status.classList.remove("connected");
      $(".status-check").textContent="○";
      $("#connection-label").textContent="DISCONNECTED";
      $("#connection-name").textContent=`${state.selectedDevice} selected`;
      $("#signal-copy").textContent="Reconnect before starting";
      button.textContent="Connect my device";
      button.onclick=()=>connect(false);
      toast("Bluetooth device disconnected");
    },{once:true});
    button.textContent="Continue";
    button.onclick=()=>openMoodScreen();
    toast(`Connected to ${device.name||state.selectedDevice}`);
  }catch(error){
    state.connectionMode="none";
    updateHomeDeviceState();
    status.classList.remove("scanning");
    status.classList.add("error");
    $(".status-check").textContent="!";
    $("#connection-label").textContent="NOT CONNECTED";
    $("#connection-name").textContent=`${state.selectedDevice} selected`;
    $("#signal-copy").textContent=error.name==="NotFoundError"?"Connection cancelled":error.message;
    button.textContent="Try again";
    button.onclick=()=>connect(false);
    toast("No Bluetooth device connected");
  }
}
function calculateRmssd(rrValues){
  if(rrValues.length<3)return 0;
  const differences=[];
  for(let i=1;i<rrValues.length;i++){const difference=rrValues[i]-rrValues[i-1];if(Math.abs(difference)<=150)differences.push(difference)}
  return differences.length<2?0:Math.sqrt(differences.reduce((sum,value)=>sum+value*value,0)/differences.length);
}
async function handleHeartMeasurement(event){
  const data=event.target.value,flags=data.getUint8(0),is16Bit=Boolean(flags&1),hasRr=Boolean(flags&16);
  let offset=1,heartRate=is16Bit?data.getUint16(offset,true):data.getUint8(offset);
  offset+=is16Bit?2:1;
  if(flags&8)offset+=2;
  if(hasRr)while(offset+1<data.byteLength){state.rrHistory.push(data.getUint16(offset,true)/1024*1000);offset+=2}
  state.rrHistory=state.rrHistory.slice(-24);
  const rmssd=calculateRmssd(state.rrHistory);
  $("#mood-heart-rate").textContent=Math.round(heartRate);
  $("#mood-rmssd").textContent=rmssd?rmssd.toFixed(1):"--";
  $("#mood-data-source").textContent=state.rrHistory.length>=4?"Live wearable":"Heart rate only";
  if(Date.now()-state.lastBioUpload>1800){
    state.lastBioUpload=Date.now();
    await fetch("/api/bio/sample",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({heart_rate:heartRate,rmssd,rr_count:state.rrHistory.length,source:"wearable"})}).catch(()=>{});
    if(state.view==="home")loadDashboard();
  }
}
async function openMoodScreen(){
  if(state.connectionMode==="demo"){
    $("#mood-heart-rate").textContent="Demo";$("#mood-rmssd").textContent="Demo";$("#mood-data-source").textContent="Simulated";
  }else{
    $("#mood-data-source").textContent=state.rrHistory.length>=4?"Live wearable":"Building live baseline";
  }
  $$(".mood-choice").forEach(choice=>{const selected=choice.dataset.sessionMood===state.mood;choice.classList.toggle("selected",selected);choice.setAttribute("aria-checked",selected)});
  show("mood");
  await updateMoodRecommendation();
}
async function updateMoodRecommendation(){
  try{
    const response=await fetch("/api/checkin",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({mood:state.mood,user:readSettings().name})}),data=await response.json();
    $("#mood-protocol-title").textContent=data.protocol.title;
    $("#mood-protocol-copy").textContent=data.protocol.description;
    state.recommendedDuration=state.mood==="drained"?480:state.mood==="stretched"?360:state.mood==="bright"?240:360;
  }catch{}
}
function enterSession(){show("session");ensureAudio();startSession()}
function updateHomeDeviceState(){
  const pill=$("#home-device-state");
  if(!pill)return;
  pill.classList.toggle("connected",state.connectionMode==="bluetooth");
  pill.classList.toggle("demo",state.connectionMode==="demo");
  pill.innerHTML=`<i></i>${state.connectionMode==="bluetooth"?(state.bluetoothDevice?.name||state.selectedDevice):state.connectionMode==="demo"?"Demo signal":"Connect device"}`;
}
async function startSession(){
  if(!state.sessionId){const settings=readSettings(),duration=state.recommendedDuration||settings.duration,device=state.connectionMode==="demo"?"Demo signal":state.bluetoothDevice?.name||state.selectedDevice;state.remaining=duration;$("#player-time").textContent=formatTime(duration);try{const r=await fetch("/api/session/start",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({mood:state.mood,duration,user:settings.name,device})}),d=await r.json();state.sessionId=d.session_id;state.baselineHrv=d.baseline_rmssd}catch{state.sessionId=`local-${Date.now()}`;state.baselineHrv=48}}
  state.running=true;$("#session-view").classList.add("running");$("#orb-label").textContent="listening";setAudioVolume(true);$("#adaptation-copy").textContent="Listening for a stable 30-second baseline...";saveInterruptedSession();
}
function toggleSession(){state.running=!state.running;$("#session-view").classList.toggle("running",state.running);$("#orb-label").textContent=state.running?"listening":"paused";setAudioVolume(state.running)}
function interruptSession(){state.running=false;setAudioVolume(false);saveInterruptedSession();$("#session-view").classList.remove("running");show("home");toast("Session paused. You can continue it anytime.")}
async function completeSession(){
  state.running=false;setAudioVolume(false);
  if(state.sessionId&&!state.sessionId.startsWith("local-")){
    await fetch("/api/session/complete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({session_id:state.sessionId})}).catch(()=>{});
  }
  clearInterruptedSession();state.sessionId=null;state.remaining=readSettings().duration;
  $("#player-time").textContent=formatTime(state.remaining);show("home");await loadDashboard();
  $("#post-reflection").hidden=false;
  toast("Session complete. Nevori learned from this response.");
}

$$("[data-go]").forEach(b=>b.onclick=()=>show(b.dataset.go));$("#start-flow").onclick=beginNewSessionFlow;
$$("[data-mobile-go]").forEach(button=>button.onclick=()=>{
  const destination=button.dataset.mobileGo;
  if(destination==="home")show("home");
  if(destination==="session")beginNewSessionFlow();
  if(destination==="learning"){show("home");setTimeout(()=>{$("#learning-details").scrollIntoView({behavior:"smooth",block:"center"});$("#modal").hidden=false},180)}
  if(destination==="settings"){populateSettings();show("settings")}
});
$("#home-device-state").onclick=()=>{
  if(state.connectionMode==="bluetooth"&&state.bluetoothDevice?.gatt?.connected)toast(`${state.bluetoothDevice.name||state.selectedDevice} is connected`);
  else show("connect");
};
function openDeviceFromReadiness(){
  if(state.connectionMode==="bluetooth"&&state.bluetoothDevice?.gatt?.connected)toast("Readiness is using live wearable data");
  else show("connect");
}
$("#home-readiness-card").onclick=openDeviceFromReadiness;
$("#home-readiness-card").onkeydown=event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();openDeviceFromReadiness()}};
$("#profile-settings").onclick=()=>{populateSettings();show("settings")};
$("#mobile-profile-settings").onclick=()=>{populateSettings();show("settings")};
$("#setting-volume").oninput=event=>{$("#setting-volume-value").textContent=`${event.target.value}%`};
$("#setting-name").oninput=event=>applyAvatar(event.target.value||"N",readSettings().photo);
$("#choose-profile-photo").onclick=()=>$("#profile-photo-input").click();
$("#profile-photo-input").onchange=event=>{
  const file=event.target.files[0];
  if(!file)return;
  if(!file.type.startsWith("image/")){toast("Please choose an image file");return}
  const reader=new FileReader();
  reader.onload=()=>{
    const image=new Image();
    image.onload=()=>{
      const size=Math.min(image.width,image.height),canvas=document.createElement("canvas"),context=canvas.getContext("2d");
      canvas.width=canvas.height=512;
      context.drawImage(image,(image.width-size)/2,(image.height-size)/2,size,size,0,0,512,512);
      const settings=readSettings();
      settings.photo=canvas.toDataURL("image/jpeg",.84);
      localStorage.setItem(SETTINGS_KEY,JSON.stringify(settings));
      applyAvatar($("#setting-name").value||settings.name,settings.photo);
      toast("Profile photo added");
    };
    image.src=reader.result;
  };
  reader.readAsDataURL(file);
  event.target.value="";
};
$("#remove-profile-photo").onclick=()=>{
  const settings=readSettings();
  settings.photo="";
  localStorage.setItem(SETTINGS_KEY,JSON.stringify(settings));
  applyAvatar($("#setting-name").value||settings.name,"");
  toast("Profile photo removed");
};
$("#save-settings").onclick=()=>{
  const current=readSettings();
  const settings={name:$("#setting-name").value.trim()||"Māris",photo:current.photo,duration:Number($("#setting-duration").value),volume:Number($("#setting-volume").value),reminders:$("#setting-reminders").checked,reduceMotion:$("#setting-motion").checked};
  localStorage.setItem(SETTINGS_KEY,JSON.stringify(settings));applySettings();show("home");toast("Settings saved");
};
$("#clear-local-data").onclick=async()=>{localStorage.removeItem(INTERRUPTED_SESSION_KEY);renderInterruptedSession();await fetch("/api/data/clear",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({user:readSettings().name})}).catch(()=>{});loadDashboard();toast("Local session data cleared")};
$$(".mood-options button").forEach(button=>button.onclick=async()=>{
  state.mood=button.dataset.mood;
  $$(".mood-options button").forEach(item=>item.classList.toggle("selected",item===button));
  $("#checkin-status").textContent=({drained:"Feeling low",stretched:"Feeling tense",steady:"Feeling okay",bright:"Feeling good"})[state.mood];
  try{
    await fetch("/api/checkin",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({mood:state.mood,user:readSettings().name})});
    await loadDashboard();
    toast("Recommendation updated");
  }catch{toast("Check-in saved locally")}
});
$$(".mood-choice").forEach(button=>button.onclick=async()=>{
  state.mood=button.dataset.sessionMood;
  $$(".mood-choice").forEach(item=>{const selected=item===button;item.classList.toggle("selected",selected);item.setAttribute("aria-checked",selected)});
  await updateMoodRecommendation();
});
$("#mood-continue").onclick=()=>show("headphones");
$$(".reflection-options button").forEach(button=>button.onclick=async()=>{
  await fetch("/api/reflection",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({reflection:button.dataset.reflection,user:readSettings().name})}).catch(()=>{});
  $("#post-reflection").hidden=true;
  toast("Thanks — Nevori saved your reflection");
});
$("#quick-start").onclick=beginNewSessionFlow;
$("#quick-start").onkeydown=event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();beginNewSessionFlow()}};
$("#resume-session").onclick=resumeInterruptedSession;
const deviceScroller=$("#device-scroll");
$$(".device-option").forEach(button=>button.addEventListener("click",event=>{
  if(event.detail===0)selectDevice(button);
}));
function updateCarousel(){
  const max=deviceScroller.scrollWidth-deviceScroller.clientWidth,ratio=max?deviceScroller.scrollLeft/max:0;
  $("#scroll-progress").style.width=`${28+ratio*72}%`;
  const cards=$$(".device-option"),center=deviceScroller.scrollLeft+deviceScroller.clientWidth/2;
  let closest=0,distance=Infinity;
  cards.forEach((card,index)=>{const cardCenter=card.offsetLeft+card.offsetWidth/2,next=Math.abs(cardCenter-center);if(next<distance){distance=next;closest=index}});
  $$(".page-dots i").forEach((item,index)=>item.classList.toggle("active",index===closest));
  $("#mobile-device-count").textContent=`${closest+1} of ${cards.length}`;
}
function moveCarousel(){
  const card=deviceScroller.querySelector(".device-option"),gap=22,step=(card?.offsetWidth||270)+gap,max=deviceScroller.scrollWidth-deviceScroller.clientWidth;
  const target=deviceScroller.scrollLeft>=max-8?0:Math.min(max,deviceScroller.scrollLeft+step);
  deviceScroller.scrollTo({left:target,behavior:"smooth"});
}
$("#device-next").onclick=moveCarousel;
deviceScroller.onscroll=()=>{
  updateCarousel();
};
let wheelTarget=0,wheelFrame=0;
deviceScroller.addEventListener("wheel",event=>{
  if(Math.abs(event.deltaY)>Math.abs(event.deltaX)){
    event.preventDefault();
    const max=deviceScroller.scrollWidth-deviceScroller.clientWidth;
    wheelTarget=Math.max(0,Math.min(max,(wheelFrame?wheelTarget:deviceScroller.scrollLeft)+event.deltaY));
    if(!wheelFrame){
      const glide=()=>{
        deviceScroller.scrollLeft+=(wheelTarget-deviceScroller.scrollLeft)*.16;
        if(Math.abs(wheelTarget-deviceScroller.scrollLeft)>.5)wheelFrame=requestAnimationFrame(glide);
        else{deviceScroller.scrollLeft=wheelTarget;wheelFrame=0}
      };
      wheelFrame=requestAnimationFrame(glide);
    }
  }
},{passive:false});
let dragStartX=0,dragStartScroll=0,dragging=false,dragMoved=false,pressedDevice=null,dragLastX=0,dragLastTime=0,dragVelocity=0,inertiaFrame=0;
deviceScroller.addEventListener("pointerdown",event=>{
  if(event.pointerType==="mouse"&&event.button!==0)return;
  cancelAnimationFrame(inertiaFrame);inertiaFrame=0;
  dragging=true;dragMoved=false;pressedDevice=event.target.closest(".device-option");
  dragStartX=event.clientX;dragStartScroll=deviceScroller.scrollLeft;dragLastX=event.clientX;dragLastTime=performance.now();dragVelocity=0;
});
deviceScroller.addEventListener("pointermove",event=>{
  if(!dragging)return;
  const distance=event.clientX-dragStartX;
  if(Math.abs(distance)>6&&!dragMoved){
    dragMoved=true;
    suppressDeviceClickUntil=Date.now()+250;
    deviceScroller.classList.add("dragging");
    deviceScroller.setPointerCapture(event.pointerId);
  }
  if(!dragMoved)return;
  event.preventDefault();
  deviceScroller.scrollLeft=dragStartScroll-distance;
  const now=performance.now(),elapsed=Math.max(1,now-dragLastTime);
  dragVelocity=(dragLastX-event.clientX)/elapsed;
  dragLastX=event.clientX;dragLastTime=now;
});
function settleCarousel(){
  const card=deviceScroller.querySelector(".device-option"),step=(card?.offsetWidth||270)+22;
  deviceScroller.scrollTo({left:Math.round(deviceScroller.scrollLeft/step)*step,behavior:"smooth"});
}
function coastCarousel(){
  if(Math.abs(dragVelocity)<.015){inertiaFrame=0;settleCarousel();return}
  deviceScroller.scrollLeft+=dragVelocity*16;dragVelocity*=.92;
  inertiaFrame=requestAnimationFrame(coastCarousel);
}
function stopCarouselDrag(event){
  if(!dragging)return;
  const shouldSelect=!dragMoved&&pressedDevice;
  dragging=false;deviceScroller.classList.remove("dragging");
  if(deviceScroller.hasPointerCapture(event.pointerId))deviceScroller.releasePointerCapture(event.pointerId);
  if(shouldSelect)selectDevice(pressedDevice);
  else if(dragMoved)inertiaFrame=requestAnimationFrame(coastCarousel);
  pressedDevice=null;dragMoved=false;
}
deviceScroller.addEventListener("pointerup",stopCarouselDrag);
deviceScroller.addEventListener("pointercancel",stopCarouselDrag);
deviceScroller.addEventListener("keydown",event=>{
  if(event.key==="ArrowRight"){event.preventDefault();moveCarousel()}
  if(event.key==="ArrowLeft"){event.preventDefault();deviceScroller.scrollTo({left:Math.max(0,deviceScroller.scrollLeft-292),behavior:"smooth"})}
});
updateCarousel();
$("#connect-device").onclick=()=>connect(false);$("#demo-session").onclick=()=>connect(true);$("#play-button").onclick=toggleSession;$("#end-session").onclick=interruptSession;
$("#headphones-ready").onclick=()=>{toast("Headphones ready · starting adaptive audio");enterSession()};
$("#without-headphones").onclick=()=>{toast("Using speaker mode · keep volume low");enterSession()};
$("#learning-details").onclick=()=>$("#modal").hidden=false;
$("#learning-details").onkeydown=event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();$("#modal").hidden=false}};
$(".modal-close").onclick=()=>$("#modal").hidden=true;$("#modal").onclick=e=>{if(e.target===e.currentTarget)e.currentTarget.hidden=true};
setInterval(()=>{renderWave();if(!state.running)return;state.remaining--;$("#player-time").textContent=formatTime(state.remaining);saveInterruptedSession();if(state.remaining<=0)completeSession()},1000);
applySettings();applyLocalTimeTheme();renderInterruptedSession();updateHomeDeviceState();loadDashboard();renderWave();setInterval(fetchState,2100);setInterval(applyLocalTimeTheme,60000);
