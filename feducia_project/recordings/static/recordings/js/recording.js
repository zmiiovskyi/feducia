document.addEventListener("DOMContentLoaded", () => {
    const videoElement = document.getElementById("camera-preview");
    const startBtn = document.getElementById("start-btn");
    const stopBtn = document.getElementById("stop-btn");
    const statusText = document.getElementById("status-text");

    let stream = null;
    let mediaRecorder = null;
    let recordedChunks = [];

    function getCookie(name) {
        const cookies = document.cookie.split(";");

        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();

            if (cookie.startsWith(name + "=")) {
                return decodeURIComponent(cookie.substring(name.length + 1));
            }
        }

        return null;
    }

    function setStatus(text, color = "#2c3e50") {
        statusText.innerText = text;
        statusText.style.color = color;
    }

    async function initCamera() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: true,
                audio: true
            });

            videoElement.srcObject = stream;

            mediaRecorder = new MediaRecorder(stream);

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    recordedChunks.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                setStatus("Saving video...");

                const blob = new Blob(recordedChunks, { type: "video/webm" });
                recordedChunks = [];

                const formData = new FormData();
                formData.append("video_file", blob, "rehearsal.webm");

                const csrfToken = getCookie("csrftoken");

                if (!csrfToken) {
                    setStatus("CSRF token not found.");
                    return;
                }

                try {
                    const response = await fetch("/save-recording/", {
                        method: "POST",
                        body: formData,
                        headers: {
                            "X-CSRFToken": csrfToken
                        }
                    });

                    if (response.ok) {
                        setStatus("Saved successfully! Ready for next recording.");
                    } else {
                        setStatus("Error saving video.");
                        console.error("Save error:", response.status, response.statusText);
                    }
                } catch (error) {
                    console.error("Network error:", error);
                    setStatus("Network error while saving.");
                }
            };
        } catch (error) {
            console.error("Camera error:", error);

            if (error.name === "NotAllowedError") {
                setStatus("Camera access denied. Please allow camera permission.");
            } else if (error.name === "NotFoundError") {
                setStatus("No camera found on this device.");
            } else {
                setStatus("Error accessing camera.");
            }

            startBtn.disabled = true;
            stopBtn.disabled = true;
        }
    }

    startBtn.addEventListener("click", () => {
        if (!mediaRecorder) {
            setStatus("Camera is not ready.");
            return;
        }

        if (mediaRecorder.state === "recording") {
            return;
        }

        recordedChunks = [];
        mediaRecorder.start();

        startBtn.disabled = true;
        stopBtn.disabled = false;

        setStatus("🔴 Recording... Speak clearly.", "#ff5252");
    });

    stopBtn.addEventListener("click", () => {
        if (!mediaRecorder) {
            return;
        }

        if (mediaRecorder.state !== "recording") {
            return;
        }

        mediaRecorder.stop();

        startBtn.disabled = false;
        stopBtn.disabled = true;
        statusText.style.color = "#2c3e50";
    });

    initCamera();
});