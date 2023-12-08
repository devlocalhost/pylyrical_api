// copy code on code tag click

window.onload = function () {
    const codeElements = document.querySelectorAll("code");

    if (codeElements.length > 0) {
        codeElements.forEach(function (codeElement) {
            codeElement.onclick = function () {
                document.execCommand("copy");
            };

            codeElement.addEventListener("copy", function (event) {
                event.preventDefault();

                if (event.clipboardData) {
                    const textToCopy =
                        codeElement.textContent || codeElement.innerText;
                    event.clipboardData.setData("text/plain", textToCopy);
                    console.log(event.clipboardData.getData("text"));
                }
            });
        });
    } else {
        console.error("No code elements found.");
    }
};

// copy code on code tag click

// "debug" stylesheet

function setCount(count) {
    localStorage.setItem("clickCount", count);
}

function getCount() {
    return parseInt(localStorage.getItem("clickCount")) || 0;
}

let isDebugStylesheetVisible = false;

function toggleStylesheet() {
    const clickCount = getCount();
    setCount(clickCount + 1);

    if (clickCount % 3 === 0) {
        isDebugStylesheetVisible = !isDebugStylesheetVisible;

        const debugStylesheet = document.getElementById("debug-stylesheet");
        debugStylesheet.disabled = !isDebugStylesheetVisible;
    }
}

// "debug" stylesheet

// pill width

window.addEventListener("scroll", function () {
    var scrollPercentage =
        (document.documentElement.scrollTop + document.body.scrollTop) /
        (document.documentElement.scrollHeight -
            document.documentElement.clientHeight);
    var barWidth = Math.min(scrollPercentage * 100, 100);
    // var barWidth = scrollPercentage * 105; // ...? lol

    document.getElementById("scrollBar").style.width = barWidth + "vw";
});

// pill width
