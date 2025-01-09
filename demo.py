import os  
import yt_dlp  
from deepgram import Deepgram  
import asyncio  
import time  
  
from pydub import AudioSegment  
import math  
import ray  
  
# Initialize Ray  
ray.init(ignore_reinit_error=True)  
  
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
  
    try:  
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:  
            info_dict = ydl.extract_info(youtube_url, download=True)  
            audio_file = ydl.prepare_filename(info_dict)  
            base, ext = os.path.splitext(audio_file)  
            audio_file = base + '.wav'  
            print(f"Audio downloaded and saved to {audio_file}")  
            return audio_file  
    except yt_dlp.utils.DownloadError as e:  
        print(f"Error downloading audio: {e}")  
        return None  
  
def split_audio(audio_file, chunk_length_ms=60000):  
    """  
    Splits the audio file into chunks of specified length.  
  
    :param audio_file: Path to the WAV audio file.  
    :param chunk_length_ms: Length of each chunk in milliseconds (default: 60,000 ms = 1 minute).  
    :return: List of chunk file paths.  
    """  
    audio = AudioSegment.from_wav(audio_file)  
    audio_length_ms = len(audio)  
    print(f"Total audio length: {audio_length_ms / 1000:.2f} seconds")  
  
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
        print(f"Exported {chunk_filename}")  
  
    return chunks  
  
@ray.remote  
def transcribe_chunk_deepgram(api_key, chunk_path, language='en-US'):  
    """  
    Transcribes a single audio chunk using Deepgram.  
  
    :param api_key: Deepgram API Key.  
    :param chunk_path: Path to the audio chunk.  
    :param language: Language code (default: 'en-US').  
    :return: Transcript string.  
    """  
    async def _transcribe():  
        dg_client = Deepgram(api_key)  
        try:  
            print(f"Transcribing {chunk_path}...")  
            with open(chunk_path, 'rb') as audio:  
                source = {'buffer': audio, 'mimetype': 'audio/wav'}  
  
                response = await dg_client.transcription.prerecorded(source, {'language': language})  
  
                transcript = response['results']['channels'][0]['alternatives'][0]['transcript']  
                print(f"Transcribed {chunk_path}")  
                return transcript  
        except Exception as e:  
            print(f"Error transcribing {chunk_path}: {e}")  
            return ""  
  
    # Run the asynchronous transcription within the synchronous remote function  
    return asyncio.run(_transcribe())  
  
def transcribe_all_chunks(api_key, chunks, language='en-US'):  
    """  
    Transcribes all audio chunks in parallel using Ray.  
  
    :param api_key: Deepgram API Key.  
    :param chunks: List of chunk file paths.  
    :param language: Language code.  
    :return: List of transcripts in order.  
    """  
    # Submit transcription tasks to Ray  
    transcribe_tasks = [  
        transcribe_chunk_deepgram.remote(api_key, chunk, language)  
        for chunk in chunks  
    ]  
  
    # Retrieve the results  
    transcripts = ray.get(transcribe_tasks)  
    return transcripts  
  
def combine_transcripts(transcripts, output_path):  
    """  
    Combines the list of transcripts into a single text file without chunk headers.  
  
    :param transcripts: List of transcript strings.  
    :param output_path: Path to save the combined transcript.  
    """  
    with open(output_path, 'w', encoding='utf-8') as f:  
        for transcript in transcripts:  
            f.write(transcript + " ")  # Adds a space between chunks  
    print(f"Combined transcript saved to {output_path}")  
  
def main(youtube_url):  
    # Create output directories if they don't exist  
    output_dir = "audio"  
    if not os.path.exists(output_dir):  
        os.makedirs(output_dir)  
  
    # Step 1: Download audio from YouTube  
    audio_file = download_audio(youtube_url, output_path=output_dir)  
    if not audio_file:  
        print("Failed to download audio. Exiting.")  
        return  
  
    # Step 2: Split audio into chunks  
    chunks = split_audio(audio_file, chunk_length_ms=60000)  # 1-minute chunks  
  
    # Step 3: Define transcript file path  
    transcript_file = os.path.splitext(audio_file)[0] + '_transcript.txt'  
  
    # Step 4: Transcribe audio chunks using Deepgram in parallel  
    API_KEY = os.getenv('DEEPGRAM_API_KEY') or ""  
    if not API_KEY:  
        print("Deepgram API Key not found. Please set the DEEPGRAM_API_KEY environment variable.")  
        return  
  
    transcripts = transcribe_all_chunks(API_KEY, chunks, language='en-US')  
  
    # Step 5: Combine transcripts  
    combine_transcripts(transcripts, transcript_file)  
  
    # Optional: Clean up chunk files  
    for chunk in chunks:  
        os.remove(chunk)  
    print("Cleaned up chunk files.")  
  
if __name__ == "__main__":  
    try:  
        # Record the start time  
        start_time = time.time()  
        youtube_url = input("Enter YouTube video URL: ").strip()  
        main(youtube_url)  
        # Record the end time  
        end_time = time.time()  
  
        # Calculate and print the duration  
        duration = end_time - start_time  
        print(f"Total execution time: {duration:.2f} seconds")  
    finally:  
        # Ensure Ray is shutdown even if an error occurs  
        ray.shutdown()  
