
Scribe v2 is now available. Learn more about the model here.


Logo
Search
/
Community
Blog
Help Center
API Pricing
Sign up

Get started
Quickstart
Agents Quickstart
Tutorials

Text to Speech

Speech to Text
Quickstart

Batch

Realtime
Client-side streaming
Server-side streaming
Transcripts and commit strategies
Event reference

Music
Text to Dialogue
Voice Changer
Voice Isolator
Dubbing
Sound effects

Voices
Forced Alignment

ElevenAgents
Multi-context WebSocket
Resources
Libraries & SDKs
Errors
Agent tooling
Zero Retention Mode
UI components
Example projects
Next.js template
Showcase
Guides
WebSockets

Migrations
Best practices
Latency optimization
Security
Breaking changes policy
Private deployment
Overview
On this page
Overview
Quickstart
Next steps
Tutorials
Speech to Text
Realtime
Server-side streaming


Copy page

Learn how to transcribe audio with ElevenLabs in realtime on the server side
Overview
The ElevenLabs Realtime Speech to Text API enables you to transcribe audio streams in real-time with ultra-low latency using the Scribe Realtime v2 model. Whether you’re building voice assistants, transcription services, or any application requiring live speech recognition, this WebSocket-based API delivers partial transcripts as you speak and committed transcripts when speech segments are complete.

Scribe v2 Realtime can be implemented on the server side to transcribe audio in realtime, either via a URL, file or your own audio stream.

The server side implementation differs from client side in a few ways:

Uses an ElevenLabs API key instead of a single use token.
Supports streaming from a URL directly, without the need to manually chunk the audio.
For streaming audio directly from the microphone, see the Client-side streaming guide.

Quickstart
1
Create an API key
Create an API key in the dashboard here, which you’ll use to securely access the API.

Store the key as a managed secret and pass it to the SDKs either as a environment variable via an .env file, or directly in your app’s configuration depending on your preference.

.env


ELEVENLABS_API_KEY=<your_api_key_here>
2
Install the SDK
We’ll also use the dotenv library to load our API key from an environment variable.


Python

TypeScript


pip install elevenlabs
pip install python-dotenv
3
Configure the SDK
The SDK provides two ways to transcribe audio in realtime: streaming from a URL or manually chunking the audio from either a file or your own audio stream.

For a full list of parameters and options the API supports, please refer to the API reference.

Stream from URL
Manual audio chunking
The easiest way to transcribe audio using Scribe is to use the official SDK. In case you aren’t able to use the SDK, you can use the WebSocket API directly. See the WebSocket example below on how to use the WebSocket API.

This example simulates a realtime transcription of an audio file.


Python

TypeScript

Python WebSocket example

TypeScript WebSocket example


import asyncio
import base64
import os
from dotenv import load_dotenv
from pathlib import Path
from elevenlabs import AudioFormat, CommitStrategy, ElevenLabs, RealtimeEvents, RealtimeAudioOptions
from pydub import AudioSegment
import sys
load_dotenv()
async def main():
    # Initialize the ElevenLabs client
    elevenlabs = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    # Create an event to signal when transcription is complete
    transcription_complete = asyncio.Event()
    # Connect with manual audio chunk mode
    connection = await elevenlabs.speech_to_text.realtime.connect(RealtimeAudioOptions(
        model_id="scribe_v2_realtime",
        audio_format=AudioFormat.PCM_16000,
        sample_rate=16000,
        commit_strategy=CommitStrategy.MANUAL,
        include_timestamps=True,
    ))
    # Set up event handlers
    def on_session_started(data):
        print(f"Session started: {data}")
        # Start sending audio once session is ready
        asyncio.create_task(send_audio())
    def on_partial_transcript(data):
        transcript = data.get('text', '')
        if transcript:
            print(f"Partial: {transcript}")
    def on_committed_transcript(data):
        transcript = data.get('text', '')
        print(f"\nCommitted transcript: {transcript}")
    def on_committed_transcript_with_timestamps(data):
        print(f"Timestamps: {data.get('words', '')}")
        print("-" * 50)
        # Signal that transcription is complete
        transcription_complete.set()
    def on_error(error):
        print(f"Error: {error}")
        transcription_complete.set()
    def on_close():
        print("Connection closed")
        transcription_complete.set()
    # Register event handlers
    connection.on(RealtimeEvents.SESSION_STARTED, on_session_started)
    connection.on(RealtimeEvents.PARTIAL_TRANSCRIPT, on_partial_transcript)
    connection.on(RealtimeEvents.COMMITTED_TRANSCRIPT, on_committed_transcript)
    connection.on(RealtimeEvents.COMMITTED_TRANSCRIPT_WITH_TIMESTAMPS, on_committed_transcript_with_timestamps)
    connection.on(RealtimeEvents.ERROR, on_error)
    connection.on(RealtimeEvents.CLOSE, on_close)
    # Convert audio file to PCM format if necessary
    def load_and_convert_audio(audio_path: str | Path, target_sample_rate: int = 16000) -> bytes:
        try:
            if str(audio_path).lower().endswith('.pcm'):
                with open(audio_path, 'rb') as f:
                    return f.read()
            audio = AudioSegment.from_file(audio_path)
            if audio.channels > 1:
                audio = audio.set_channels(1)
            if audio.frame_rate != target_sample_rate:
                audio = audio.set_frame_rate(target_sample_rate)
            audio = audio.set_sample_width(2)
            return audio.raw_data
        except Exception as e:
            print(f"Error loading audio: {e}")
            sys.exit(1)
    async def send_audio():
        """Send audio chunks from an audio file"""
        audio_file_path = Path("/path/to/audio.mp3")
        try:
            # Read the audio file
            audio_data = load_and_convert_audio(audio_file_path)
            # Split into chunks (1 second of audio = 32000 bytes at 16kHz, 16-bit)
            chunk_size = 32000
            chunks = [audio_data[i:i + chunk_size] for i in range(0, len(audio_data), chunk_size)]
            # Send each chunk
            for i, chunk in enumerate(chunks):
                chunk_base64 = base64.b64encode(chunk).decode('utf-8')
                await connection.send({"audio_base_64": chunk_base64, "sample_rate": 16000})
                # Wait 1 second between chunks (simulating real-time)
                if i < len(chunks) - 1:
                    await asyncio.sleep(1)
            # Small delay before committing to let last chunk process
            await asyncio.sleep(0.5)
            # Commit to finalize segment and get committed transcript
            await connection.commit()
        except Exception as e:
            print(f"Error sending audio: {e}")
            transcription_complete.set()
    try:
        # Wait for transcription to complete
        await transcription_complete.wait()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        await connection.close()
if __name__ == "__main__":
    asyncio.run(main())
4
Execute the code

Python

TypeScript


python example.py
You will see the transcription of the audio file printed to the console in partial and committed transcripts.

Next steps
Learn how to handle transcripts and commit strategies in the Transcripts and commit strategies section, and review the list of events and error types that can be received from the Realtime Speech to Text API in the Event reference section.

Was this page helpful?
Yes
No
Previous
Transcripts and commit strategies
Learn how to handle transcripts and commit strategies with ElevenLabs in Realtime Speech to Text
Next
Built with
Server-side streaming | ElevenLabs Documentation
US flagEnglish


Or send a message
Powered by ElevenLabs Agents


Scribe v2 is now available. Learn more about the model here.


Logo
Search
/
Community
Blog
Help Center
API Pricing
Sign up

Get started
Quickstart
Agents Quickstart
Tutorials

Text to Speech

Speech to Text
Quickstart

Batch

Realtime
Client-side streaming
Server-side streaming
Transcripts and commit strategies
Event reference

Music
Text to Dialogue
Voice Changer
Voice Isolator
Dubbing
Sound effects

Voices
Forced Alignment

ElevenAgents
Multi-context WebSocket
Resources
Libraries & SDKs
Errors
Agent tooling
Zero Retention Mode
UI components
Example projects
Next.js template
Showcase
Guides
WebSockets

Migrations
Best practices
Latency optimization
Security
Breaking changes policy
Private deployment
Overview
On this page
Overview
Commit strategies
Manual commit
Sending previous text context
Voice Activity Detection (VAD)
Supported audio formats
Best practices
Audio quality
Chunk size
Tutorials
Speech to Text
Realtime
Transcripts and commit strategies

Copy page

Learn how to handle transcripts and commit strategies with ElevenLabs in Realtime Speech to Text
Overview
When transcribing audio, you will receive partial and committed transcripts.

Partial transcripts - the interim results of the transcription
Committed transcripts - the final results of the transcription segment that are sent when a “commit” message is received. A session can have multiple committed transcripts.
The commit transcript can optionally contain word-level timestamps. This is only received when the “include timestamps” option is set to true.


Python

TypeScript

React

JavaScript


# Initialize the connection
connection = await elevenlabs.speech_to_text.realtime.connect(RealtimeUrlOptions(
  model_id="scribe_v2_realtime",
  include_timestamps=True, # Include this to receive the RealtimeEvents.COMMITTED_TRANSCRIPT_WITH_TIMESTAMPS event with word-level timestamps
))
Commit strategies
When sending audio chunks via the WebSocket, transcript segments can be committed in two ways: Manual Commit or Voice Activity Detection (VAD).

Manual commit
With the manual commit strategy, you control when to commit transcript segments. This is the strategy that is used by default. Committing a segment will clear the processed accumulated transcript and start a new segment without losing context. Committing every 20-30 seconds is good practice to improve latency. By default the stream will be automatically committed every 90 seconds.

For best results, commit during silence periods or another logical point like a turn model.

Transcript processing starts after the first 2 seconds of audio are sent.

Python

TypeScript


await connection.send({
  "audio_base_64": audio_base_64,
  "sample_rate": 16000,
})
# When ready to finalize the segment
await connection.commit()
Committing manually several times in a short sequence can degrade model performance.

Sending previous text context
When sending audio for transcription, you can send previous text context alongside the first audio chunk to help the model understand the context of the speech. This is useful in a few scenarios:

Agent text for conversational AI use cases - Allows the model to more easily understand the context of the conversation and produce better transcriptions.
Reconnection after a network error - This allows the model to continue transcribing, using the previous text as guidance.
General contextual information - A short description of what the transcription will be about helps the model understand the context.
Sending previous_text context is only possible when sending the first audio chunk via connection.send(). Sending it in subsequent chunks will result in an error. Previous text works best when it’s under 50 characters long.


Python

TypeScript


await connection.send({
  "audio_base_64": audio_base_64,
  "previous_text": "The previous text context",
})
Voice Activity Detection (VAD)
With the VAD strategy, the transcription engine automatically detects speech and silence segments. When a silence threshold is reached, the transcription engine will commit the transcript segment automatically.

When transcribing audio from the microphone in the client-side integration, it is recommended to use the VAD strategy.


Client

Python

TypeScript


from dotenv import load_dotenv
from elevenlabs import AudioFormat, CommitStrategy, ElevenLabs, RealtimeAudioOptions
load_dotenv()
elevenlabs = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
connection = await elevenlabs.speech_to_text.realtime.connect(
    RealtimeAudioOptions(
        model_id="scribe_v2_realtime",
        audio_format=AudioFormat.PCM_16000,
        commit_strategy=CommitStrategy.VAD,
        vad_silence_threshold_secs=1.5,
        vad_threshold=0.4,
        min_speech_duration_ms=100,
        min_silence_duration_ms=100,
    )
)
Supported audio formats
Format	Sample Rate	Description
pcm_8000	8 kHz	16-bit PCM, little-endian
pcm_16000	16 kHz	16-bit PCM, little-endian (recommended)
pcm_22050	22.05 kHz	16-bit PCM, little-endian
pcm_24000	24 kHz	16-bit PCM, little-endian
pcm_44100	44.1 kHz	16-bit PCM, little-endian
pcm_48000	48 kHz	16-bit PCM, little-endian
ulaw_8000	8 kHz	8-bit μ-law encoding
Best practices
Audio quality
For best results, use a 16kHz sample rate for an optimum balance of quality and bandwidth.
Ensure clean audio input with minimal background noise.
Use an appropriate microphone gain to avoid clipping.
Only mono audio is supported at this time.
Chunk size
Send audio chunks of 0.1 - 1 second in length for smooth streaming.
Smaller chunks result in lower latency but more overhead.
Larger chunks are more efficient but can introduce latency.
Was this page helpful?
Yes
No
Previous
Realtime event reference
Reference of the events received from the Realtime Speech to Text API
Next
Built with
Transcripts and commit strategies | ElevenLabs Documentation
US flagEnglish


Or send a message
Powered by ElevenLabs Agents


Scribe v2 is now available. Learn more about the model here.


Logo
Search
/
Community
Blog
Help Center
API Pricing
Sign up

Get started
Quickstart
Agents Quickstart
Tutorials

Text to Speech

Speech to Text
Quickstart

Batch

Realtime
Client-side streaming
Server-side streaming
Transcripts and commit strategies
Event reference

Music
Text to Dialogue
Voice Changer
Voice Isolator
Dubbing
Sound effects

Voices
Forced Alignment

ElevenAgents
Multi-context WebSocket
Resources
Libraries & SDKs
Errors
Agent tooling
Zero Retention Mode
UI components
Example projects
Next.js template
Showcase
Guides
WebSockets

Migrations
Best practices
Latency optimization
Security
Breaking changes policy
Private deployment
Overview
On this page
Sent events
Received events
Error handling
Tutorials
Speech to Text
Realtime
Realtime event reference

Copy page

Reference of the events received from the Realtime Speech to Text API
Review the API reference for the Realtime Speech to Text API for more information on the API and its options.

Sent events
Event	Description	When to use
input_audio_chunk	Send audio data for transcription	Continuously while streaming audio
Received events
Event	Description	When received
session_started	Confirms connection and returns session configuration	Immediately after WebSocket connection is established
partial_transcript	Live transcript update	During audio processing, before a commit is made
committed_transcript	Transcript of the audio segment	After a commit (either manual or VAD triggered)
committed_transcript_with_timestamps	Sent after the committed transcript of the audio segment. Contains word-level timestamps	Sent after the committed transcript of the audio segment. Only received when include_timestamps=true is included in the query parameters
Error handling
If an error occurs, an error message will be returned before the WebSocket connection is closed.

Error Type	Description
auth_error	An error occurred while authenticating the request. Double check your API key
quota_exceeded	You have exceeded your usage quota
transcriber_error	An error occurred while transcribing the audio.
input_error	An error occurred while processing the audio chunk. Likely due to invalid input format or parameters
error	A generic server error
commit_throttled	The commit was throttled due to too many commit requests made in a short period of time
transcriber_error	An error occurred while transcribing the audio.
unaccepted_terms	You haven’t accepted the terms of service to use Scribe. Please review and accept the terms & conditions in the ElevenLabs dashboard
rate_limited	You are rate limited. Please reduce the amount of requests made in a short period of time
queue_overflow	The processing queue is full. Please send fewer requests made in a short period of time
resource_exhausted	Server resources are at capacity. Please try again later
session_time_limit_exceeded	Maximum session time has been reached. Please start a new session or upgrade your subscription
chunk_size_exceeded	The audio chunk size is too large. Please reduce the chunk size
insufficient_audio_activity	You haven’t sent enough audio activity to maintain the connection
Was this page helpful?
Yes
No
Previous
Music quickstart
Learn how to generate music with Eleven Music.
Next
Built with
Realtime event reference | ElevenLabs Documentation
US flagEnglish


Or send a message
Powered by ElevenLabs Agents

