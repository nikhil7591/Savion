import React, { useState } from "react";

function VoiceInput({ onResult, onFieldsExtracted }) {
  const [recording, setRecording] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [chunks, setChunks] = useState([]);
  const [lastTranscription, setLastTranscription] = useState("");

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      setMediaRecorder(recorder);
      setChunks([]);
      setLastTranscription("");

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) setChunks((prev) => [...prev, e.data]);
      };

      recorder.start();
      setRecording(true);
    } catch (err) {
      console.error("Mic access denied", err);
      alert("Please allow microphone access to use voice input.");
    }
  };

  const stopRecording = () => {
    if (!mediaRecorder) return;
    setProcessing(true);
    
    mediaRecorder.stop();
    mediaRecorder.onstop = async () => {
      const blob = new Blob(chunks, { type: "audio/webm" });
      const formData = new FormData();
      formData.append("file", blob, "voice.webm");

      try {
        const res = await fetch("http://localhost:8000/api/transcribe", {
          method: "POST",
          body: formData,
        });
        
        if (!res.ok) {
          throw new Error(`Server error: ${res.status}`);
        }
        
        const data = await res.json();
        console.log("Voice transcription response:", data);
        
        setLastTranscription(data.text);
        
        // Call the result callback with transcribed text
        if (onResult) {
          onResult(data.text);
        }
        
        // Call the fields callback if fields were extracted
        if (onFieldsExtracted && data.fields) {
          onFieldsExtracted(data.fields);
        }
        
      } catch (err) {
        console.error("Transcription failed", err);
        alert("Failed to process voice input. Please try again.");
      } finally {
        setRecording(false);
        setProcessing(false);
        
        // Stop all tracks to release microphone
        if (mediaRecorder && mediaRecorder.stream) {
          mediaRecorder.stream.getTracks().forEach(track => track.stop());
        }
      }
    };
  };

  const getButtonText = () => {
    if (processing) return "🔄 Processing...";
    if (recording) return "🛑 Stop Recording";
    return "🎙️ Voice Input";
  };

  const getButtonClass = () => {
    let className = "voice-btn";
    if (processing) className += " processing";
    else if (recording) className += " stop";
    return className;
  };

  return (
    <div className="voice-input-container">
      <button 
        className={getButtonClass()}
        onClick={recording ? stopRecording : startRecording}
        disabled={processing}
      >
        {getButtonText()}
      </button>
      
      {lastTranscription && (
        <div className="transcription-display">
          <small>📝 "{lastTranscription}"</small>
        </div>
      )}
      
      {recording && (
        <div className="recording-indicator">
          <span className="pulse-dot"></span>
          Recording...
        </div>
      )}
    </div>
  );
}

export default VoiceInput;