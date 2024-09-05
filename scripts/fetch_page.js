const getContestPage = async () => {
    const contestId = process.argv[2];
    const response = await fetch(`https://codeforces.com/contest/${contestId}`, {
      "headers": {
        "sec-ch-ua": "\"Chromium\";v=\"128\", \"Not;A=Brand\";v=\"24\", \"Google Chrome\";v=\"128\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "upgrade-insecure-requests": "1",
        "Referer": `https://codeforces.com/contest/${contestId}`,
        "Referrer-Policy": "strict-origin-when-cross-origin"
      },
      "body": null,
      "method": "GET"
    });
    if (response.status != 200) {
        process.exit(1)
    }
    const body = await response.text()
    return body;
}

getContestPage().then(res => console.log(res))


