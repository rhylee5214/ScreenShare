const statusEl=document.getElementById("status"), preview=document.getElementById("preview");
const startBtn=document.getElementById("start"), stopBtn=document.getElementById("stop");
const path=location.pathname.split("/"), requestId=path[path.length-1];
let socket=null,pc=null,stream=null,viewerReady=false;
async function config(){const r=await fetch("/api/config");return r.json()}
function waitIce(){if(pc.iceGatheringState==="complete")return Promise.resolve();return new Promise(resolve=>{
 const f=()=>{if(pc.iceGatheringState==="complete"){pc.removeEventListener("icegatheringstatechange",f);resolve()}};
 pc.addEventListener("icegatheringstatechange",f);
})}
async function connect(){
 const c=await config();pc=new RTCPeerConnection({iceServers:c.ice_servers});
 socket=new WebSocket(`${location.protocol==="https:"?"wss":"ws"}://${location.host}/ws/${encodeURIComponent(requestId)}/host`);
 socket.onopen=()=>statusEl.textContent="Connected securely. Waiting for the viewer to open the live view.";
 socket.onmessage=async ev=>{
  const m=JSON.parse(ev.data);
  if(m.type==="peer_joined"){viewerReady=true;statusEl.textContent="Viewer connected. Choose a screen to begin sharing."}
  if(m.type==="answer"){await pc.setRemoteDescription({type:"answer",sdp:m.sdp});statusEl.textContent="LIVE — your screen is being shared."}
  if(m.type==="peer_disconnected"){viewerReady=false;statusEl.textContent="Viewer disconnected. Sharing can be stopped."; }
  if(m.type==="stop"){stopShare("The viewer disconnected the session.");}
 };
 socket.onclose=()=>{if(stream)stopShare("Connection closed.");};
}
startBtn.onclick=async()=>{
 try{
  if(!viewerReady){statusEl.textContent="Wait until the approved viewer opens the live view.";return}
  stream=await navigator.mediaDevices.getDisplayMedia({video:true,audio:false});
  preview.srcObject=stream;
  stream.getTracks().forEach(t=>{pc.addTrack(t,stream);t.onended=()=>stopShare("Screen sharing ended.");});
  const offer=await pc.createOffer();await pc.setLocalDescription(offer);await waitIce();
  socket.send(JSON.stringify({type:"offer",sdp:pc.localDescription.sdp}));
  startBtn.disabled=true;stopBtn.disabled=false;
  statusEl.textContent="Screen selected. Connecting live viewer…";
 }catch(e){statusEl.textContent="Screen sharing was cancelled or unavailable: "+e.message;stopShare("Not sharing.");}
};
function stopShare(message){
 if(stream){stream.getTracks().forEach(t=>t.stop());stream=null}
 preview.srcObject=null;
 if(socket&&socket.readyState===WebSocket.OPEN)socket.send(JSON.stringify({type:"stop"}));
 if(pc){pc.close();pc=null}
 if(socket){socket.close();socket=null}
 startBtn.disabled=false;stopBtn.disabled=true;statusEl.textContent=message;
}
stopBtn.onclick=()=>stopShare("You stopped sharing.");
connect().catch(e=>statusEl.textContent="Could not connect: "+e.message);
