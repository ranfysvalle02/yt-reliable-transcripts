# yt-reliable-transcripts

---

# YouTube Audio Transcription Pipeline with Python, Deepgram, and Ray  
   
Transcribing audio from YouTube videos can greatly enhance accessibility, content analysis, and information retrieval. Whether you're a content creator, educator, or researcher, automating this process can save time and streamline workflows. This guide provides a comprehensive overview of building a robust transcription pipeline using Python, Deepgram's Speech-to-Text API, and Ray for parallel processing.  
   
---  
   
## Pipeline Overview  
   
The transcription pipeline consists of the following components:  
   
1. **Download Audio**: Extract the best available audio stream from a YouTube video using `yt-dlp`.  
2. **Split Audio**: Divide the downloaded audio into 1-minute WAV chunks with `pydub` for efficient processing.  
3. **Transcribe Audio**: Utilize Deepgram's Speech-to-Text API to convert audio chunks into text.  
4. **Parallel Processing**: Employ Ray to handle multiple transcription tasks concurrently, enhancing speed and efficiency.  
5. **Combine Transcripts**: Merge individual transcripts into a single, cohesive document.  
   
This modular approach ensures scalability, efficiency, and ease of maintenance.  
   
---  
   
## Step-by-Step Implementation  
   
### 1. Downloading Audio from YouTube  
   
Utilize `yt-dlp` to download the highest quality audio stream from a YouTube video:  
   
```python  
import yt_dlp  
import os  
   
def download_audio(youtube_url, output_path='audio'):  
    ydl_opts = {  
        'format': 'bestaudio/best',  
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),  
        'postprocessors': [{  
            'key': 'FFmpegExtractAudio',  
            'preferredcodec': 'wav',  
            'preferredquality': '192',  
        }],  
        'quiet': False,  
        'no_warnings': True,  
    }  
  
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  
        info_dict = ydl.extract_info(youtube_url, download=True)  
        audio_file = ydl.prepare_filename(info_dict)  
        base, ext = os.path.splitext(audio_file)  
        audio_file = base + '.wav'  
        return audio_file  
```  
   
**Key Points:**  
   
- **Format Selection**: Downloads the best available audio quality.  
- **Output Template**: Saves the file in the specified `output_path` with the video's title.  
- **Post-processing**: Converts the audio to WAV format using FFmpeg for compatibility.  
   
### 2. Splitting Audio into Chunks  
   
Large audio files can be resource-intensive. Splitting them into smaller chunks allows for more efficient processing and reduces costs when using transcription services.  
   
```python  
from pydub import AudioSegment  
import math  
   
def split_audio(audio_file, chunk_length_ms=60000):  
    audio = AudioSegment.from_wav(audio_file)  
    audio_length_ms = len(audio)  
    num_chunks = math.ceil(audio_length_ms / chunk_length_ms)  
    chunks = []  
    base, ext = os.path.splitext(audio_file)  
  
    for i in range(num_chunks):  
        start_ms = i * chunk_length_ms  
        end_ms = min((i + 1) * chunk_length_ms, audio_length_ms)  
        chunk = audio[start_ms:end_ms]  
        chunk_filename = f"{base}_chunk_{i + 1}{ext}"  
        chunk.export(chunk_filename, format="wav")  
        chunks.append(chunk_filename)  
  
    return chunks  
```  
   
**Key Points:**  
   
- **Chunk Duration**: Default is set to 60,000 milliseconds (1 minute).  
- **Export Format**: Each chunk is exported as a separate WAV file for consistency.  
   
### 3. Transcribing Audio with Deepgram  
   
Deepgram provides a powerful Speech-to-Text API. Here's how to integrate it for transcribing audio chunks:  
   
```python  
from deepgram import Deepgram  
import asyncio  
   
async def transcribe_chunk(api_key, chunk_path, language='en-US'):  
    dg_client = Deepgram(api_key)  
    with open(chunk_path, 'rb') as audio:  
        source = {'buffer': audio, 'mimetype': 'audio/wav'}  
        response = await dg_client.transcription.prerecorded(source, {'language': language})  
        transcript = response['results']['channels'][0]['alternatives'][0]['transcript']  
        return transcript  
```  
   
**Key Points:**  
   
- **Asynchronous Operation**: Utilizes `asyncio` for non-blocking HTTP requests to Deepgram.  
- **Language Support**: Configurable via the `language` parameter (default is `'en-US'`).  
   
### 4. Parallel Processing with Ray  
   
Processing each audio chunk sequentially can be time-consuming. Ray allows for parallel execution, significantly speeding up the transcription process.  
   
```python  
import ray  
import asyncio  
   
# Initialize Ray  
ray.init(ignore_reinit_error=True)  
   
@ray.remote  
def transcribe_chunk_deepgram(api_key, chunk_path, language='en-US'):  
    return asyncio.run(transcribe_chunk(api_key, chunk_path, language))  
```  
   
**Key Points:**  
   
- **Ray Initialization**: Ensures that Ray is set up for parallel task execution.  
- **Remote Function**: Decorated with `@ray.remote` to enable distributed processing.  
   
### 5. Combining Transcripts  
   
After transcribing all chunks, merge the individual transcripts into a single, readable document.  
   
```python  
def combine_transcripts(transcripts, output_path):  
    with open(output_path, 'w', encoding='utf-8') as f:  
        for transcript in transcripts:  
            f.write(transcript + " ")  
```  
   
**Key Points:**  
   
- **Sequential Merging**: Ensures that the order of transcripts matches the original audio sequence.  
- **Output Format**: Saves the combined transcript as a plain text file.  
   
---  
   
## Usage Instructions  
   
1. **Set Up Environment Variables**  
  
   Ensure your Deepgram API key is set as an environment variable (`DEEPGRAM_API_KEY`).  
   
2. **Run the Transcription Pipeline**  
  
   Execute your Python script (e.g., `transcribe.py`) from the command line:  
  
   ```bash  
   python demo.py  
   ```  
  
   You'll be prompted to enter the YouTube video URL:  
  
   ```  
   Enter YouTube video URL: https://www.youtube.com/watch?v=example_video  
   ```  
   
3. **Process Flow Overview**  
  
   - **Audio Download**: The script downloads the audio in WAV format.  
   - **Audio Splitting**: The audio is divided into 1-minute chunks.  
   - **Parallel Transcription**: Each chunk is transcribed concurrently using Ray and Deepgram.  
   - **Transcript Compilation**: Individual transcripts are combined into a single text file.  
   - **Cleanup**: Temporary audio chunks are deleted to free up space.  
   
4. **Output**  
  
   Upon successful execution, you'll find a transcript text file in the `audio` directory, named similarly to the original YouTube video title (e.g., `video_title_transcript.txt`).  
   
---  
