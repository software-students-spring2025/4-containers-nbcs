// web-app/static/js/main_index.js
let mediaRecorder;
let audioChunks = [];
let recordingId = null;
let checkTranscriptionInterval = null;

document.getElementById('start-recording').addEventListener('click', async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.addEventListener('dataavailable', event => {
            audioChunks.push(event.data);
        });
        
        mediaRecorder.addEventListener('stop', () => {
            uploadRecording();
        });
        
        mediaRecorder.start();
        
        document.getElementById('start-recording').disabled = true;
        document.getElementById('stop-recording').disabled = false;
        document.getElementById('status').textContent = 'Recording...';
    } catch (err) {
        console.error('Error accessing microphone:', err);
        document.getElementById('status').textContent = 'Error accessing microphone. Please check permissions.';
    }
});

document.getElementById('stop-recording').addEventListener('click', () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        document.getElementById('start-recording').disabled = false;
        document.getElementById('stop-recording').disabled = true;
        document.getElementById('status').textContent = 'Processing recording...';
    }
});

document.getElementById('view-recordings').addEventListener('click', () => {
    window.location.href = '/recordings';
});

async function uploadRecording() {
    const meetingName = document.getElementById('meeting-name').value || 'Unnamed Meeting';
    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
    const formData = new FormData();
    
    formData.append('audio', audioBlob);
    formData.append('meeting_name', meetingName);
    
    try {
        const response = await fetch('/save_recording', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            recordingId = data.recording_id;
            document.getElementById('status').textContent = 'Recording saved. Waiting for transcription...';
            
            // Start checking for transcription
            checkTranscriptionInterval = setInterval(checkTranscription, 3000);
        } else {
            document.getElementById('status').textContent = `Error: ${data.error || 'Unknown error'}`;
        }
    } catch (err) {
        console.error('Error uploading recording:', err);
        document.getElementById('status').textContent = 'Error uploading recording. Please try again.';
    }
}

async function checkTranscription() {
    if (!recordingId) return;
    
    try {
        const response = await fetch(`/get_transcription/${recordingId}`);
        const data = await response.json();
        
        if (data.success) {
            if (data.status === 'completed' && data.transcription) {
                clearInterval(checkTranscriptionInterval);
                document.getElementById('status').textContent = 'Transcription completed!';
                document.getElementById('transcription').textContent = data.transcription;
                document.getElementById('transcription-container').style.display = 'block';
            } else {
                document.getElementById('status').textContent = `Transcription ${data.status}...`;
            }
        } else {
            document.getElementById('status').textContent = `Error: ${data.error || 'Unknown error'}`;
            clearInterval(checkTranscriptionInterval);
        }
    } catch (err) {
        console.error('Error checking transcription:', err);
        document.getElementById('status').textContent = 'Error checking transcription status.';
        clearInterval(checkTranscriptionInterval);
    }
}