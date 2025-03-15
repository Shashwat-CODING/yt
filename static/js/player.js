document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('extractForm');
    const urlInput = document.getElementById('youtubeUrl');
    const extractBtn = document.getElementById('extractBtn');
    const playerContainer = document.getElementById('playerContainer');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const errorAlert = document.getElementById('errorAlert');
    const audioPlayer = document.getElementById('audioPlayer');
    const playPauseBtn = document.getElementById('playPauseBtn');
    const progressBar = document.querySelector('.progress-bar');
    const currentTimeSpan = document.getElementById('currentTime');
    const durationSpan = document.getElementById('duration');

    function formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        seconds = Math.floor(seconds % 60);
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }

    function showError(message) {
        errorAlert.textContent = message;
        errorAlert.classList.remove('d-none');
        loadingSpinner.classList.add('d-none');
        playerContainer.classList.add('d-none');
    }

    function updatePlayPauseButton() {
        const icon = playPauseBtn.querySelector('i');
        if (audioPlayer.paused) {
            icon.classList.remove('fa-pause');
            icon.classList.add('fa-play');
        } else {
            icon.classList.remove('fa-play');
            icon.classList.add('fa-pause');
        }
    }

    playPauseBtn.addEventListener('click', () => {
        if (audioPlayer.paused) {
            audioPlayer.play();
        } else {
            audioPlayer.pause();
        }
    });

    audioPlayer.addEventListener('play', updatePlayPauseButton);
    audioPlayer.addEventListener('pause', updatePlayPauseButton);

    audioPlayer.addEventListener('timeupdate', () => {
        const progress = (audioPlayer.currentTime / audioPlayer.duration) * 100;
        progressBar.style.width = `${progress}%`;
        currentTimeSpan.textContent = formatTime(audioPlayer.currentTime);
    });

    audioPlayer.addEventListener('loadedmetadata', () => {
        durationSpan.textContent = formatTime(audioPlayer.duration);
    });

    audioPlayer.addEventListener('ended', () => {
        progressBar.style.width = '0%';
        currentTimeSpan.textContent = '0:00';
        updatePlayPauseButton();
    });

    document.querySelector('.progress').addEventListener('click', (e) => {
        const progressBar = e.currentTarget;
        const clickPosition = e.offsetX / progressBar.offsetWidth;
        audioPlayer.currentTime = clickPosition * audioPlayer.duration;
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        errorAlert.classList.add('d-none');
        loadingSpinner.classList.remove('d-none');
        playerContainer.classList.add('d-none');
        
        const formData = new FormData();
        formData.append('url', urlInput.value);

        try {
            const response = await fetch('/extract', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to extract audio');
            }

            document.getElementById('thumbnail').src = data.thumbnail;
            document.getElementById('videoTitle').textContent = data.title;
            document.getElementById('videoAuthor').textContent = data.author;
            
            audioPlayer.src = data.url;
            audioPlayer.load();
            
            loadingSpinner.classList.add('d-none');
            playerContainer.classList.remove('d-none');
            
            // Auto-play when ready
            audioPlayer.play().catch(() => {
                console.log('Auto-play prevented');
            });

        } catch (error) {
            showError(error.message);
        }
    });
});
