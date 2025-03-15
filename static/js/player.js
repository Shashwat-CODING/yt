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
    
    // Track if we're using a proxy for the current audio
    let usingProxy = false;
    let instances = null;
    let originalAudioUrl = '';

    // Fetch available proxy instances
    async function fetchInstances() {
        try {
            const response = await fetch('https://raw.githubusercontent.com/n-ce/Uma/main/dynamic_instances.json');
            instances = await response.json();
            console.log('Available proxy instances:', instances);
        } catch (error) {
            console.error('Failed to fetch proxy instances:', error);
        }
    }
    
    // Call this on page load
    fetchInstances();

    function getProxyUrl(originalUrl) {
        if (!instances || (!instances.piped.length && !instances.invidious.length)) {
            return null;
        }
        
        // Try to extract the parameters and host from the URL
        try {
            const url = new URL(originalUrl);
            const host = url.hostname;
            
            // Use a random instance from available proxies
            let proxyBase;
            if (instances.piped.length > 0) {
                proxyBase = instances.piped[Math.floor(Math.random() * instances.piped.length)];
            } else {
                proxyBase = instances.invidious[Math.floor(Math.random() * instances.invidious.length)];
            }
            
            // Construct the proxied URL - keep all query parameters and add host
            const proxiedUrl = `${proxyBase}/videoplayback${url.search}&host=${host}`;
            console.log('Proxied URL:', proxiedUrl);
            return proxiedUrl;
        } catch (error) {
            console.error('Failed to create proxy URL:', error);
            return null;
        }
    }

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

    // Handle audio errors, including 403
    audioPlayer.addEventListener('error', async (e) => {
        console.error('Audio player error:', audioPlayer.error);
        
        // If we get a 403 error and haven't tried proxy yet
        if (audioPlayer.error && audioPlayer.error.code === 4 && !usingProxy && originalAudioUrl) {
            console.log('Attempting to use proxy due to 403 error');
            const proxyUrl = getProxyUrl(originalAudioUrl);
            
            if (proxyUrl) {
                usingProxy = true;
                audioPlayer.src = proxyUrl;
                audioPlayer.load();
                
                try {
                    await audioPlayer.play();
                } catch (playError) {
                    console.error('Failed to play using proxy:', playError);
                    showError('Failed to play audio even with proxy. Please try another video.');
                }
            } else {
                showError('Cannot access audio. Proxy servers unavailable.');
            }
        } else if (usingProxy) {
            // Already tried proxy and still failing
            showError('Cannot access audio. Please try another video.');
        }
    });

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
        
        // Reset proxy status for new request
        usingProxy = false;
        
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
            
            // Store original URL before playing
            originalAudioUrl = data.url;
            audioPlayer.src = data.url;
            audioPlayer.load();
            
            loadingSpinner.classList.add('d-none');
            playerContainer.classList.remove('d-none');
            
            // Auto-play when ready
            audioPlayer.play().catch((error) => {
                console.log('Auto-play prevented:', error);
                // Don't show error yet, let the error event handler deal with it
            });

        } catch (error) {
            showError(error.message);
        }
    });
});
