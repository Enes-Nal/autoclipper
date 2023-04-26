const image = document.getElementById("guessimage")
const next = document.getElementById("continue")

const manbutton = document.getElementById("mananswer")
const womenbutton = document.getElementById("womenanswer")

const progresspercent = document.getElementById("progresspercent")
const progressbar = document.getElementById("progressbar")

const correctalert=document.getElementById("rightalert")
const wrongalert=document.getElementById("wrongalert")

var answer = null
var imageid=null
newimage()
next.onclick = function () {
    newimage()
    manbutton.disabled = false
    womenbutton.disabled = false
}

async function myAnswer(e) {
    result = (e.id == "mananswer" && answer == 1) || 
    (e.id == "womenanswer" && answer == 0)
    if (result == true) {
        correctalert.style.visibility="visible"
    }else{
        wrongalert.style.visibility="visible"
    }
    answer = null
    manbutton.disabled = true
    womenbutton.disabled = true

    next.disabled = false

    fetch("/vote", {
        method: "post",
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
            "answer": result,
            "id":imageid
        })
    }).then((response) => {
        console.log(response)
    });
}

function newimage() {
    next.disabled = true
    wrongalert.style.visibility="hidden"
    correctalert.style.visibility="hidden"
    a = randomNumber(1, 394)

    imageid=a

    image.src = "/img/guess/" + a + ".jpg";

    fetch("/imginfo", {
        method: "post",
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ "id": a }
        )
    }).then(
        response => response.json(),
        error => console.log('An error occurred.', error)
    ).then(res => {
        answer = res.answer
        if(res.difficulty==null){
            difficulty=0
        }else{
            difficulty = res.difficulty
        }
        
        progressbar.value = difficulty
        progresspercent.innerHTML = difficulty
    })
}

function randomNumber(min, max) {
    return Math.floor(Math.random() * (max - min) + 1);
}