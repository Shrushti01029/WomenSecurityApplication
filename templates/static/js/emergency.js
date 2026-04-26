// ====================
// Global Variables
// ====================
let map, marker, watchID;
let alarmSound;
let mediaRecorder
let audioChunks = []
let audioBlob = null
let timerInterval
let seconds = 0
let userLat;
let userLon;

// ====================
// SOS Alert - Direct send to server & alert
// ====================
function sendSOS() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function(position) {
            let lat = position.coords.latitude;
            let lon = position.coords.longitude;
            let location = lat + "," + lon;

            fetch("/send_sos", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({location: location})
            })
            .then(res => res.json())
            .then(data => {
                alert("🚨 SOS Alert Sent To Emergency Contacts!");
            })
            .catch(err => console.error(err));
        });
    } else {
        alert("Geolocation not supported by your browser!");
    }
}

// ====================
// Prepare SOS - share message via WhatsApp, SMS, Email
// ====================
function prepareSOS() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function(position) {
            let lat = position.coords.latitude;
            let lon = position.coords.longitude;

            let mapLink = "https://maps.google.com/?q=" + lat + "," + lon;
            let message = "🚨 SOS ALERT! I need help! My location: " + mapLink;

            let whatsappLink = "https://wa.me/?text=" + encodeURIComponent(message);
            let smsLink = "sms:?body=" + encodeURIComponent(message);
            let emailLink = "mailto:?subject=Emergency&body=" + encodeURIComponent(message);

            document.getElementById("sosBox").innerHTML = `
                <p>Emergency Message Ready:</p>
                <textarea readonly style="width:80%; height:60px;">${message}</textarea>
                <br><br>
                <button onclick="copyText('${message}')">Copy Message</button>
                <a href="${whatsappLink}" target="_blank">
                    <button>Share on WhatsApp</button>
                </a>
                <a href="${smsLink}">
                    <button>Send via SMS</button>
                </a>
                <a href="${emailLink}">
                    <button>Send via Email</button>
                </a>
            `;
        });
    } else {
        alert("Geolocation is not supported by your browser.");
    }
}

// ====================
// Copy text to clipboard
// ====================
function copyText(text){
    navigator.clipboard.writeText(text).then(() => {
        alert("Message copied!");
    });
}

// ====================
// Share current location
// ====================
function shareLocation() {
    navigator.geolocation.getCurrentPosition(function(pos){
        let lat = pos.coords.latitude;
        let lon = pos.coords.longitude;
        let mapLink = "https://maps.google.com/?q=" + lat + "," + lon;
        let msg = "🚨 I am in danger. Track my location: " + mapLink;

        document.getElementById("locationBox").innerHTML = `
            <p>Location Link:</p>
            <input value="${mapLink}" id="copyLink" style="width:80%">
            <button onclick="copyLocation()">Copy Link</button>
            <a href="https://wa.me/?text=${encodeURIComponent(msg)}" target="_blank">
                <button>Share on WhatsApp</button>
            </a>
        `;
    });
}

// ====================
// Copy location
// ====================
function copyLocation(){
    let copyText = document.getElementById("copyLink");
    copyText.select();
    document.execCommand("copy");
    alert("Location copied!");
}

// ====================
// Live Tracking
// ====================
function startTracking(){

    map = L.map('map').setView([20,78],5)

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{
        maxZoom:19
    }).addTo(map)

    watchID = navigator.geolocation.watchPosition(function(pos){

        let lat = pos.coords.latitude
        let lon = pos.coords.longitude
        let accuracy = pos.coords.accuracy

        if(marker){
            marker.setLatLng([lat,lon])
        }
        else{
            marker = L.marker([lat,lon]).addTo(map)
        }

        map.setView([lat,lon],15)

        let mapLink = "https://maps.google.com/?q="+lat+","+lon

        document.getElementById("trackingInfo").innerHTML = `
        <p><b>Latitude:</b> ${lat}</p>
        <p><b>Longitude:</b> ${lon}</p>
        <p><b>Accuracy:</b> ${accuracy} meters</p>
        <p><b>Tracking Time:</b> ${new Date().toLocaleTimeString()}</p>
        `

        let message = "📍 Live Location Tracking: "+mapLink

        let whatsapp = "https://wa.me/?text="+encodeURIComponent(message)
        let sms = "sms:?body="+encodeURIComponent(message)
        let email = "mailto:?subject=Live Location&body="+encodeURIComponent(message)

        document.getElementById("shareTracking").innerHTML = `
        <h3>Share Your Live Location</h3>
        <input id="trackLink" value="${mapLink}" style="width:80%">
        <button onclick="copyTracking()">Copy Link</button>

        <br><br>

        <a href="${whatsapp}" target="_blank">
        <button>Share on WhatsApp</button></a>

        <a href="${sms}">
        <button>Send SMS</button></a>

        <a href="${email}">
        <button>Email</button></a>
        `

        fetch("/save_tracking",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({lat:lat,lon:lon})
        })

    })
}

function stopTracking(){
    navigator.geolocation.clearWatch(watchID)
    alert("Tracking stopped")
}

function copyTracking(){
    let copy = document.getElementById("trackLink")
    copy.select()
    document.execCommand("copy")
    alert("Tracking link copied!")
}

// ====================
// Alarm
// ====================
function playAlarm(){
    alarmSound = new Audio("/static/sounds/siren.mp3");
    alarmSound.loop = true;
    alarmSound.play();
    alert("Alarm activated!");
}

function stopAlarm(){
    if(alarmSound){ alarmSound.pause(); alarmSound.currentTime = 0; }
}

// ====================
// Voice SOS
// ====================





/* =========================
   ENABLE MICROPHONE
========================= */

function enableMic(){

navigator.mediaDevices.getUserMedia({audio:true})

.then(function(stream){

document.getElementById("recordStatus").innerText =
"✅ Microphone enabled";

stream.getTracks().forEach(track => track.stop());

})

.catch(function(error){

alert("⚠ Please allow microphone access");

console.log(error);

});

}

// ====================
// START RECORDING
// ====================

function startVoiceRecording(){

navigator.mediaDevices.getUserMedia({audio:true})
.then(stream=>{

mediaRecorder=new MediaRecorder(stream)

audioChunks=[]

mediaRecorder.start()

seconds=0

document.getElementById("recordStatus").innerText="🔴 Recording Started"

timerInterval=setInterval(()=>{
seconds++
document.getElementById("recordTimer").innerText="Recording Time: "+seconds+" sec"
},1000)

mediaRecorder.ondataavailable=e=>{
audioChunks.push(e.data)
}

// get location
navigator.geolocation.getCurrentPosition(pos=>{
userLat=pos.coords.latitude
userLon=pos.coords.longitude
})

})

}


// ====================
// STOP RECORDING
// ====================

function stopVoiceRecording(){

if(!mediaRecorder){
alert("Recording not started")
return
}

mediaRecorder.stop()

clearInterval(timerInterval)

mediaRecorder.onstop=function(){

audioBlob=new Blob(audioChunks,{type:"audio/webm"})

let audioURL=URL.createObjectURL(audioBlob)

let player=document.getElementById("audioPlayback")

player.src=audioURL
player.style.display="block"

document.getElementById("recordStatus").innerText="✅ Recording Saved"

saveRecording()

}

}


// ====================
// SAVE RECORDING
// ====================

function saveRecording(){

let formData=new FormData()

formData.append("audio",audioBlob)
formData.append("lat",userLat)
formData.append("lon",userLon)

fetch("/save_voice_evidence",{
method:"POST",
body:formData
})
.then(res=>res.json())
.then(data=>{
console.log(data)
})

}


// ====================
// PLAY RECORDING
// ====================

function playRecording(){

let player=document.getElementById("audioPlayback")

if(!audioBlob){
alert("No recording available")
return
}

player.play()

}


// ====================
// DELETE RECORDING
// ====================

function deleteRecording(){

audioBlob=null

document.getElementById("audioPlayback").style.display="none"

document.getElementById("recordStatus").innerText="Recording Deleted"

document.getElementById("recordTimer").innerText=""

}


// ====================
// SHARE RECORDING
// ====================

function shareRecording(){

if(!audioBlob){
alert("Please record audio first")
return
}

navigator.geolocation.getCurrentPosition(function(position){

let lat=position.coords.latitude
let lon=position.coords.longitude

let locationLink="https://maps.google.com/?q="+lat+","+lon

let message="🚨 Emergency Voice SOS!\nLocation: "+locationLink

let whatsapp="https://wa.me/?text="+encodeURIComponent(message)

window.open(whatsapp)

})

}



// ====================
// Emergency Contacts
// ====================
function addContact(){
    let name = document.getElementById("name").value
    let phone = document.getElementById("phone").value

    if(!name || !phone){
        alert("Please enter name and phone")
        return
    }

    fetch("/add_contact", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({name:name, phone:phone})
    })
    .then(res => res.json())
    .then(data => {
        alert(data.message)
        location.reload()  // refresh to show new contact
    })
}

// ====================
// Find Nearby Police Stations (GPS Based)
// ====================
function findPolice(){

if(navigator.geolocation){

navigator.geolocation.getCurrentPosition(function(position){

let lat = position.coords.latitude
let lon = position.coords.longitude

let mapURL = "https://www.google.com/maps/search/police+station/@"
            + lat + "," + lon + ",14z"

window.open(mapURL, "_blank")

})

}else{

alert("Geolocation not supported by this browser")

}

}




// MAIN SOS BUTTON


function triggerSOS(){

let status = document.getElementById("sosStatus");
status.innerText="🚨 Activating Emergency...";

navigator.geolocation.getCurrentPosition(function(position){

let lat = position.coords.latitude;
let lon = position.coords.longitude;

let locationLink = "https://maps.google.com/?q="+lat+","+lon;

let message = "🚨 SOS ALERT 🚨%0A%0A"+
"Priya needs help immediately.%0A%0A"+
"📍 Live Location:%0A"+locationLink+
"%0A%0APlease contact or reach immediately.";


// 📞 ADD MULTIPLE EMERGENCY CONTACTS HERE
let contacts = [
"8468937119",  // Mother
"9766633525",  // Friend
"7822093620"   // Brother
];

contacts.forEach(function(number){

let whatsappURL = "https://wa.me/"+number+"?text="+message;

window.open(whatsappURL,"_blank");

});

status.innerText="✅ SOS message opened for emergency contacts";

});
}