require('dotenv').config()
const express = require('express');
const app = express();
const bodyParser = require('body-parser');
const mysql = require('mysql');

app.use(bodyParser.urlencoded({ extended: false }));
app.use(bodyParser.json())
app.use(express.static(__dirname + '/public'));

const connection = mysql.createConnection({
    host: process.env.ipSQL,
    user: process.env.hostSQL,
    password: process.env.passwordSQL,
    database: process.env.databaseSQL,
});

connection.connect(function (err) {
    if (err) {
        console.error('error connecting: ' + err.stack);
        return;
    }
    console.log("[+] SQL Successfully connected with id `" + connection.threadId + '`')
});

app.get('/', async (req, res) => {
    res.render('index.ejs', {})
})

app.post('/vote', function (req, res) {
    data = req.body
    if (typeof data.answer === "boolean" &&
        typeof data.id === "number" &&
        data.id > 0 &&
        data.id <= 400
    ) {
        id = (data.id).toString()
        if (data.answer == true) {
            column = "correct"
        } else {
            column = "incorrect"
        }

        connection.query("UPDATE Images SET " + column + " = " + column + " + 1  WHERE id = " + id, function (err, result) {
            if (err) throw err;
        });

        res.send("OK")
        console.log("[+] " + JSON.stringify(req.body))
    }
})

app.post('/imginfo', function (req, res) {
    connection.query("select male,correct,incorrect from Images WHERE id =" + req.body.id, function (err, result, fields) {
        if (err) throw err;
        
        data = {}
        correct=result[0].correct
        incorrect=result[0].incorrect
        
        percentage = Math.round((incorrect / (correct + incorrect)) * 100,2)
        data.difficulty=percentage
        data.answer = result[0].male
        res.send(JSON.stringify(data))
    });
})

function randomNumber(min, max) {
    return Math.floor(Math.random() * (max - min) + 1);
}

app.listen(parseInt(process.env.PORT), () => console.log('[+] Server started on port  ' + process.env.PORT))