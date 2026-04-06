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

    async function saveRecording() {
        setStatus("Saving video...");

        const blob = new Blob(recordedChunks, { type: "video/webm" });
        recordedChunks = [];

        const formData = new FormData();
        formData.append("video_file", blob, "rehearsal.webm");

        const csrfToken = getCookie("csrftoken");

        if (!csrfToken) {
            setStatus("CSRF token not found.", "#ff5252");
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

            const data = await response.json();

            if (!response.ok) {
                console.error("Save error:", data);
                setStatus("Error saving video.", "#ff5252");
                startBtn.disabled = false;
                return;
            }

            if (data.status === "success" && data.id) {
                setStatus("Video saved. Redirecting...");
                window.location.href = `/loading/${data.id}/`;
                return;
            }

            setStatus("Unexpected server response.", "#ff5252");
            console.error("Unexpected response:", data);
            startBtn.disabled = false;
        } catch (error) {
            console.error("Network error:", error);
            setStatus("Network error while saving.", "#ff5252");
            startBtn.disabled = false;
        }
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
                stopBtn.disabled = true;
                startBtn.disabled = true;

                await saveRecording();
            };

            setStatus("Camera is ready.");
        } catch (error) {
            console.error("Camera error:", error);

            if (error.name === "NotAllowedError") {
                setStatus("Camera access denied. Please allow camera permission.", "#ff5252");
            } else if (error.name === "NotFoundError") {
                setStatus("No camera found on this device.", "#ff5252");
            } else {
                setStatus("Error accessing camera.", "#ff5252");
            }

            startBtn.disabled = true;
            stopBtn.disabled = true;
        }
    }

    startBtn.addEventListener("click", () => {
        if (!mediaRecorder) {
            setStatus("Camera is not ready.", "#ff5252");
            return;
        }

        if (mediaRecorder.state === "recording") {
            return;
        }

        recordedChunks = [];
        mediaRecorder.start();

        startBtn.disabled = true;
        stopBtn.disabled = false;

        setStatus("Recording... Speak clearly.", "#ff5252");
    });

    stopBtn.addEventListener("click", () => {
        if (!mediaRecorder) {
            return;
        }

        if (mediaRecorder.state !== "recording") {
            return;
        }

        setStatus("Stopping recording...");
        mediaRecorder.stop();
    });

    stopBtn.disabled = true;
    initCamera();
});