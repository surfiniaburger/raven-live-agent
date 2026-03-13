import { useState, useRef, useCallback, useEffect } from 'react';
import { AudioStreamer } from './audioStreamer';
import { AudioRecorder } from './audioRecorder';

export function useGeminiSocket(url, { enableInterrupt = true } = {}) {
    const [status, setStatus] = useState('DISCONNECTED');
    const [lastMessage, setLastMessage] = useState(null);
    const ws = useRef(null);
    const streamRef = useRef(null);
    const intervalRef = useRef(null);
    const lastInterruptAt = useRef(0);
    const audioStreamer = useRef(new AudioStreamer(24000)); // Default to 24kHz for Gemini Live
    const audioRecorder = useRef(new AudioRecorder(16000)); // Record at 16kHz for Gemini Input

    const connect = useCallback(() => {
        if (ws.current?.readyState === WebSocket.OPEN) return;

        ws.current = new WebSocket(url);

        ws.current.onopen = () => {
            console.log('Connected to Gemini Socket');
            setStatus('CONNECTED');
        };

        ws.current.onclose = () => {
            console.log('Disconnected from Gemini Socket');
            setStatus('DISCONNECTED');
            stopStream();
        };

        ws.current.onerror = (err) => {
            console.error('Socket error:', err);
            setStatus('ERROR');
        };

        ws.current.onmessage = async (event) => {
            try {
                const msg = JSON.parse(event.data);
                setLastMessage(msg);

                // Handle documented client events (when present)
                if (msg.type) {
                    if (msg.type === 'ping' && ws.current?.readyState === WebSocket.OPEN) {
                        ws.current.send(JSON.stringify({ type: 'pong' }));
                    }
                    if (msg.type === 'audio' && msg.audio_event?.audio_base_64) {
                        audioStreamer.current.resume();
                        audioStreamer.current.addPCM16(msg.audio_event.audio_base_64);
                    }
                    if (msg.type === 'user_transcript' && msg.user_transcription_event?.user_transcript) {
                        setLastMessage({
                            content: { parts: [{ text: `[SYSTEM:USER_TRANSCRIPT] ${msg.user_transcription_event.user_transcript}` }] }
                        });
                    }
                    if (msg.type === 'agent_response' && msg.agent_response_event?.agent_response) {
                        setLastMessage({
                            content: { parts: [{ text: msg.agent_response_event.agent_response }] }
                        });
                    }
                    if (msg.type === 'agent_response_correction' && msg.agent_response_correction_event?.corrected_agent_response) {
                        setLastMessage({
                            content: { parts: [{ text: msg.agent_response_correction_event.corrected_agent_response }] }
                        });
                        audioStreamer.current.stop();
                    }
                    if (msg.type === 'vad_score' && msg.vad_score_event?.vad_score !== undefined) {
                        // Optional: VAD score could be surfaced in UI later.
                        console.debug('[useGeminiSocket] VAD score', msg.vad_score_event.vad_score);
                    }
                }

                // Helper to extract parts from various possible event structures
                let parts = [];
                if (msg.serverContent?.modelTurn?.parts) {
                    parts = msg.serverContent.modelTurn.parts;
                } else if (msg.content?.parts) {
                    parts = msg.content.parts;
                }

                if (parts.length > 0) {
                    parts.forEach(part => {
                        // Handle Tool Calls (The "Sync" logic)
                        if (part.functionCall) {
                            if (part.functionCall.name === 'report_digit') {
                                const count = parseInt(part.functionCall.args.count, 10);
                                setLastMessage({ type: 'DIGIT_DETECTED', value: count });
                            }
                        }

                        // Handle Audio (The AI's voice)
                        if (part.inlineData && part.inlineData.data) {
                            audioStreamer.current.resume();
                            audioStreamer.current.addPCM16(part.inlineData.data);
                        }
                    });
                }
                
                // Handle interruption and turn boundaries
                if (msg.interrupted) {
                    console.warn('[useGeminiSocket] Interrupted event received');
                    audioStreamer.current.stop();
                } else if (msg.turnComplete) {
                    console.log('[useGeminiSocket] Turn complete');
                    audioStreamer.current.stop();
                }
            } catch (e) {
                console.error('Failed to parse message', e, event.data.slice(0, 100));
            }
        };
    }, [url]);

    const sendInterrupt = useCallback(() => {
        if (!enableInterrupt) return;
        if (ws.current?.readyState === WebSocket.OPEN) {
            console.warn('[useGeminiSocket] Sending interrupt');
            ws.current.send(JSON.stringify({ type: 'interrupt' }));
        } else {
            console.warn('[useGeminiSocket] Interrupt skipped; WS not open');
        }
    }, [enableInterrupt]);

    const startStream = useCallback(async (videoElement) => {
        try {
            // 1. Start Video Stream
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            videoElement.srcObject = stream;
            streamRef.current = stream;
            await videoElement.play();

            // 2. Start Audio Recording (Microphone)
            try {
                let packetCount = 0;
                await audioRecorder.current.start((base64Audio) => {
                    if (ws.current?.readyState === WebSocket.OPEN) {
                        const now = Date.now();
                        if (audioStreamer.current.isPlaying && now - lastInterruptAt.current > 700) {
                            lastInterruptAt.current = now;
                            sendInterrupt();
                        }
                        packetCount++;
                        if (packetCount % 50 === 0) console.log(`[useGeminiSocket] Sending Audio Packet #${packetCount}, size: ${base64Audio.length}`);
                        ws.current.send(JSON.stringify({
                            type: 'audio',
                            data: base64Audio,
                            sampleRate: 16000
                        }));
                    } else {
                        if (packetCount % 50 === 0) console.warn('[useGeminiSocket] WS not OPEN, cannot send audio');
                    }
                });
                console.log("Microphone recording started");
            } catch (authErr) {
                console.error("Microphone access denied or error:", authErr);
            }

            // 3. Setup Video Frame Capture loop
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const width = 640;
            const height = 480;
            canvas.width = width;
            canvas.height = height;

            intervalRef.current = setInterval(() => {
                if (ws.current?.readyState === WebSocket.OPEN) {
                    ctx.drawImage(videoElement, 0, 0, width, height);
                    const base64 = canvas.toDataURL('image/jpeg', 0.6).split(',')[1];
                    // ADK format: { type: "image", data: base64, mimeType: "image/jpeg" }
                    ws.current.send(JSON.stringify({
                        type: 'image',
                        data: base64,
                        mimeType: 'image/jpeg'
                    }));
                }
            }, 500); // 2 FPS
        } catch (err) {
            console.error('Error accessing camera:', err);
        }
    }, []);

    const stopStream = useCallback(() => {
        // Stop Video
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }
        // Stop Audio
        audioRecorder.current.stop();

        // Clear Interval
        if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
        }
    }, []);

    useEffect(() => {
        return () => {
            stopStream();
            if (ws.current) ws.current.close();
        };
    }, [stopStream]);

    const disconnect = useCallback(() => {
        if (ws.current) {
            ws.current.close();
            ws.current = null;
        }
        setStatus('DISCONNECTED');
        stopStream();
    }, [stopStream]);

    return { status, lastMessage, connect, disconnect, startStream, stopStream };
}
