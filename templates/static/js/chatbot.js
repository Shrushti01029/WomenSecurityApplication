function sendMessage(){

let input = document.getElementById("userInput");

let message = input.value;

if(message.trim() === "") return;

addMessage(message,"user");

fetch("/chatbot_response",{

method:"POST",
headers:{
"Content-Type":"application/json"
},

body:JSON.stringify({message:message})

})

.then(res=>res.json())

.then(data=>{

addMessage(data.response,"bot");

})

input.value="";

}

function addMessage(text,type){

let chatbox=document.getElementById("chatbox");

let div=document.createElement("div");

div.className=type;

div.innerHTML="<span>"+text+"</span>";

chatbox.appendChild(div);

chatbox.scrollTop=chatbox.scrollHeight;

}

function sendQuick(text){

document.getElementById("userInput").value=text;

sendMessage();

}

/* Voice Recognition */



function startVoice() {

const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();

recognition.lang = "en-IN";
recognition.start();

recognition.onresult = function(event) {

let speech = event.results[0][0].transcript;

document.getElementById("userInput").value = speech;

};

recognition.onerror = function(event) {
alert("Microphone error: " + event.error);
};

}


fetch("/chatbot_response", {
method: "POST",
headers: {
"Content-Type": "application/json"
},
body: JSON.stringify({message: userMessage})
})
.then(response => response.json())
.then(data => {

addMessage("bot", data.response)

// 🔊 Speak chatbot response
speak(data.response)

})

function speak(text){

let speech = new SpeechSynthesisUtterance()

speech.text = text

speech.lang = "en-US"

window.speechSynthesis.speak(speech)

}