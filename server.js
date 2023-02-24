'use strict';

const express = require('express');
const Wappalyzer = require('wappalyzer');

// Constants
const PORT = 8080;
const HOST = '0.0.0.0';

const options = {
    debug: false,
    delay: 500,
    headers: {},
    maxDepth: 3,
    maxUrls: 10,
    maxWait: 15000,
    recursive: true,
    probe: true,
    userAgent: 'Wappalyzer',
    htmlMaxCols: 2000,
    htmlMaxRows: 2000,
    noScripts: false,
};
const wappalyzer = new Wappalyzer(options)

// 
async function init_wappalyzer() {
    try {
        await wappalyzer.init();
    } catch (error) {
        console.error(error)
    }
}

// App
const app = express();
app.get('/:url', async (req, res) => {
    // Optionally set additional request headers
    const headers = {};
    const url = req.params.url.toString();
    console.log(url);
    try {
        await wappalyzer.init();
        const site = await wappalyzer.open(url, headers);

        // Optionally capture and output errors
        site.on('error', console.error);

        const results = await site.analyze();
        await site.destroy();
        res.send(JSON.stringify(results, null, 2));
    } catch (e) {
        console.error(e.toString())
        //await wappalyzer.destroy()
    } finally {
        await wappalyzer.destroy()
        res.status(200).send();
    }
    //await site.destroy();
});

app.listen(PORT, HOST, function () {

});
app.on('listening', function () {
    // server ready to accept connections here
});
console.log(`Running on http://${HOST}:${PORT}`);