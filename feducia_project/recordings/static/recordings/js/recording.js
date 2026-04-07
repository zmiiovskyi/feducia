document.addEventListener("DOMContentLoaded", () => {
    const videoElement = document.getElementById("camera-preview");
    const startBtn = document.getElementById("start-btn");
    const stopBtn = document.getElementById("stop-btn");
    const openModalBtn = document.getElementById("open-modal-btn");
    const deleteTextBtn = document.getElementById("delete-text-btn");
    const saveTextBtn = document.getElementById("save-text-btn");
    const modal = document.getElementById("text-modal");
    const teleInput = document.getElementById("teleprompter-input");
    const teleOverlay = document.getElementById("teleprompter-overlay");
    const teleText = document.getElementById("teleprompter-text");
    const timerDisplay = document.getElementById("timer-display");
    const statusText = document.getElementById("status-text");
    const speedButtons = document.querySelectorAll(".btn-speed");

    let stream = null;
    let mediaRecorder = null;
    let recordedChunks = [];
    let timerInterval = null;
    let seconds = 0;
    let pausedByModal = false;

    let currentWpm = 145;
    let isScrolling = false;
    let scrollOffset = 0;
    let animationFrameId = null;
    let lastTime = 0;

    const svgIcon = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
        </svg>
    `;

    function getCsrfToken() {
        const input = document.querySelector("[name=csrfmiddlewaretoken]");
        return input ? input.value : null;
    }

    function setStatus(text, color = "#2c3e50") {
        statusText.innerText = text;
        statusText.style.color = color;
    }

    speedButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            speedButtons.forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            currentWpm = parseInt(btn.dataset.speed, 10);
        });
    });

    function scrollLoop(timestamp) {
        if (!lastTime) {
            lastTime = timestamp;
        }

        const deltaTime = timestamp - lastTime;
        lastTime = timestamp;

        if (isScrolling) {
            const content = teleInput.value.trim();
            const wordCount = content ? content.split(/\s+/).length : 1;
            const durationSec = (wordCount / currentWpm) * 60;
            const totalDistance = teleOverlay.offsetHeight + teleText.offsetHeight;
            const speedPxPerSec = totalDistance / durationSec;

            scrollOffset += speedPxPerSec * (deltaTime / 1000);
            teleText.style.transform = `translateY(-${scrollOffset}px) scaleX(1)`;

            if (scrollOffset < totalDistance) {
                animationFrameId = requestAnimationFrame(scrollLoop);
            } else {
                isScrolling = false;
                animationFrameId = null;
            }
        }
    }

    function startScrolling() {
        if (!isScrolling) {
            isScrolling = true;
            lastTime = performance.now();
            animationFrameId = requestAnimationFrame(scrollLoop);
        }
    }

    function stopScrolling() {
        isScrolling = false;

        if (animationFrameId) {
            cancelAnimationFrame(animationFrameId);
            animationFrameId = null;
        }
    }

    function resetScrolling() {
        stopScrolling();
        scrollOffset = 0;
        teleText.style.transform = "translateY(0px) scaleX(1)";
    }

    function updateTimer() {
        seconds += 1;
        const mins = Math.floor(seconds / 60).toString().padStart(2, "0");
        const secs = (seconds % 60).toString().padStart(2, "0");
        timerDisplay.innerText = `${mins}:${secs}`;
    }

    function closeModal() {
        modal.style.display = "none";

        if (teleInput.value.trim() !== "") {
            openModalBtn.innerHTML = `${svgIcon} Change Teleprompter`;
            deleteTextBtn.style.display = "flex";
            teleText.innerText = teleInput.value.trim();
        } else {
            openModalBtn.innerHTML = `${svgIcon} Add Teleprompter`;
            deleteTextBtn.style.display = "none";
            teleOverlay.style.display = "none";
            teleText.innerText = "";
        }

        if (pausedByModal && mediaRecorder && mediaRecorder.state === "paused") {
            mediaRecorder.resume();
            timerInterval = setInterval(updateTimer, 1000);
            startScrolling();
            startBtn.innerHTML = "⏸ Pause";
            startBtn.className = "btn btn-pause";
            pausedByModal = false;
        }
    }

    openModalBtn.addEventListener("click", () => {
        modal.style.display = "flex";

        if (mediaRecorder && mediaRecorder.state === "recording") {
            pausedByModal = true;
            mediaRecorder.pause();
            clearInterval(timerInterval);
            stopScrolling();
            startBtn.innerHTML = "▶ Resume";
            startBtn.className = "btn btn-start";
        }
    });

    saveTextBtn.addEventListener("click", closeModal);

    window.addEventListener("click", (event) => {
        if (event.target === modal) {
            closeModal();
        }
    });

    deleteTextBtn.addEventListener("click", () => {
        teleInput.value = "";
        openModalBtn.innerHTML = `${svgIcon} Add Teleprompter`;
        deleteTextBtn.style.display = "none";
        teleOverlay.style.display = "none";
        teleText.innerText = "";
        resetScrolling();
    });

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
                formData.append("teleprompter_text", teleInput.value.trim());

                const csrfToken = getCsrfToken();

                if (!csrfToken) {
                    setStatus("CSRF token not found.");
                    startBtn.disabled = false;
                    stopBtn.disabled = true;
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

                    let data = null;

                    try {
                        data = await response.json();
                    } catch (error) {
                        console.error("JSON parse error:", error);
                    }

                    if (response.ok && data && data.status === "success" && data.id) {
                        setStatus("Saved successfully! Redirecting...");
                         window.location.href = `/loading/${data.id}/`;
                        return;
                    }

                    console.error("Save error:", {
                        status: response.status,
                        statusText: response.statusText,
                        data: data
                    });

                    setStatus("Error saving video.");
                    startBtn.disabled = false;
                    stopBtn.disabled = true;
                } catch (error) {
                    console.error("Network error:", error);
                    setStatus("Network error while saving.");
                    startBtn.disabled = false;
                    stopBtn.disabled = true;
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

        if (mediaRecorder.state === "inactive") {
            recordedChunks = [];
            mediaRecorder.start();

            seconds = 0;
            timerDisplay.innerText = "00:00";

            statusText.style.display = "none";
            timerDisplay.style.display = "block";

            timerInterval = setInterval(updateTimer, 1000);

            resetScrolling();

            if (teleInput.value.trim() !== "") {
                teleOverlay.style.display = "block";
                teleText.innerText = teleInput.value.trim();
                startScrolling();
            }

            startBtn.innerHTML = "⏸ Pause";
            startBtn.className = "btn btn-pause";
            stopBtn.disabled = false;
            return;
        }

        if (mediaRecorder.state === "recording") {
            mediaRecorder.pause();
            clearInterval(timerInterval);
            stopScrolling();
            startBtn.innerHTML = "▶ Resume";
            startBtn.className = "btn btn-start";
            return;
        }

        if (mediaRecorder.state === "paused") {
            mediaRecorder.resume();
            timerInterval = setInterval(updateTimer, 1000);

            if (teleInput.value.trim() !== "") {
                startScrolling();
            }

            startBtn.innerHTML = "⏸ Pause";
            startBtn.className = "btn btn-pause";
        }
    });

    stopBtn.addEventListener("click", () => {
        if (!mediaRecorder || mediaRecorder.state === "inactive") {
            return;
        }

        mediaRecorder.stop();
        clearInterval(timerInterval);
        resetScrolling();
        teleOverlay.style.display = "none";

        seconds = 0;
        timerDisplay.innerText = "00:00";

        timerDisplay.style.display = "none";
        statusText.style.display = "block";
        setStatus("Processing video...");

        startBtn.innerHTML = "▶ Start";
        startBtn.className = "btn btn-start";
        startBtn.disabled = true;
        stopBtn.disabled = true;
    });

    initCamera();
});