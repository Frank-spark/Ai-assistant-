"""Meeting Recorder and Transcription Service for Reflex Executive Assistant."""

import logging
import asyncio
import json
import tempfile
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, BinaryIO
from dataclasses import dataclass
import wave
import pyaudio
import speech_recognition as sr
from pydub import AudioSegment
from pydub.playback import play
import openai
import whisper

from ..config import get_settings
from ..storage.models import Meeting, MeetingTranscript, MeetingAnalysis
from ..storage.db import get_db_session
from ..ai.chain import get_ai_chain

logger = logging.getLogger(__name__)


@dataclass
class MeetingRecordingConfig:
    """Configuration for meeting recording."""
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    format: int = pyaudio.paInt16
    max_duration: int = 3600  # 1 hour max
    auto_transcribe: bool = True
    auto_analyze: bool = True
    save_audio: bool = True


class MeetingRecorder:
    """Records, transcribes, and analyzes executive meetings."""
    
    def __init__(self, config: Optional[MeetingRecordingConfig] = None):
        self.config = config or MeetingRecordingConfig()
        self.settings = get_settings()
        self.audio = pyaudio.PyAudio()
        self.recognizer = sr.Recognizer()
        self.whisper_model = None
        self.is_recording = False
        self.recording_frames = []
        self.current_meeting_id = None
        
        # Initialize Whisper model for transcription
        try:
            self.whisper_model = whisper.load_model("base")
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load Whisper model: {e}")
    
    async def start_recording(self, meeting_id: str, meeting_title: str) -> Dict[str, Any]:
        """Start recording a meeting."""
        try:
            if self.is_recording:
                raise ValueError("Already recording a meeting")
            
            logger.info(f"Starting recording for meeting: {meeting_title} (ID: {meeting_id})")
            
            self.current_meeting_id = meeting_id
            self.recording_frames = []
            self.is_recording = True
            
            # Start recording in background
            asyncio.create_task(self._record_audio())
            
            # Create meeting record in database
            db_session = get_db_session()
            meeting = Meeting(
                id=meeting_id,
                title=meeting_title,
                start_time=datetime.now(timezone.utc),
                end_time=None,
                attendees=[],  # Will be populated later
                organizer="executive",  # Default to executive
                meeting_type="executive",
                status="recording"
            )
            db_session.add(meeting)
            db_session.commit()
            db_session.close()
            
            return {
                "status": "recording_started",
                "meeting_id": meeting_id,
                "message": f"Recording started for: {meeting_title}"
            }
            
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            raise
    
    async def stop_recording(self) -> Dict[str, Any]:
        """Stop recording and process the meeting."""
        try:
            if not self.is_recording:
                raise ValueError("No active recording")
            
            logger.info("Stopping recording and processing meeting")
            
            self.is_recording = False
            
            # Save audio file
            audio_file_path = await self._save_audio()
            
            # Transcribe audio
            transcript = await self._transcribe_audio(audio_file_path)
            
            # Analyze transcript
            analysis = await self._analyze_transcript(transcript)
            
            # Update meeting record
            await self._update_meeting_record(transcript, analysis)
            
            # Clean up audio file if not saving
            if not self.config.save_audio and os.path.exists(audio_file_path):
                os.remove(audio_file_path)
            
            return {
                "status": "recording_completed",
                "meeting_id": self.current_meeting_id,
                "transcript_length": len(transcript),
                "analysis_summary": analysis.get("summary", ""),
                "action_items": analysis.get("action_items", [])
            }
            
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            raise
    
    async def _record_audio(self) -> None:
        """Record audio in background."""
        try:
            stream = self.audio.open(
                format=self.config.format,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                frames_per_buffer=self.config.chunk_size
            )
            
            logger.info("Audio recording started")
            
            while self.is_recording:
                try:
                    data = stream.read(self.config.chunk_size)
                    self.recording_frames.append(data)
                except Exception as e:
                    logger.error(f"Error reading audio data: {e}")
                    break
            
            stream.stop_stream()
            stream.close()
            
            logger.info("Audio recording stopped")
            
        except Exception as e:
            logger.error(f"Error in audio recording: {e}")
    
    async def _save_audio(self) -> str:
        """Save recorded audio to file."""
        try:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False,
                dir=tempfile.gettempdir()
            )
            temp_file_path = temp_file.name
            temp_file.close()
            
            # Write audio data to WAV file
            with wave.open(temp_file_path, 'wb') as wf:
                wf.setnchannels(self.config.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.config.format))
                wf.setframerate(self.config.sample_rate)
                wf.writeframes(b''.join(self.recording_frames))
            
            logger.info(f"Audio saved to: {temp_file_path}")
            return temp_file_path
            
        except Exception as e:
            logger.error(f"Error saving audio: {e}")
            raise
    
    async def _transcribe_audio(self, audio_file_path: str) -> str:
        """Transcribe audio using Whisper."""
        try:
            logger.info("Starting audio transcription")
            
            if self.whisper_model:
                # Use Whisper for transcription
                result = self.whisper_model.transcribe(audio_file_path)
                transcript = result["text"]
            else:
                # Fallback to speech recognition
                with sr.AudioFile(audio_file_path) as source:
                    audio = self.recognizer.record(source)
                    transcript = self.recognizer.recognize_google(audio)
            
            logger.info(f"Transcription completed: {len(transcript)} characters")
            return transcript
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return "Transcription failed"
    
    async def _analyze_transcript(self, transcript: str) -> Dict[str, Any]:
        """Analyze transcript using AI."""
        try:
            logger.info("Starting transcript analysis")
            
            ai_chain = get_ai_chain()
            
            analysis_prompt = f"""
            Analyze this executive meeting transcript and provide:
            
            1. **Summary**: Key points discussed
            2. **Action Items**: Specific tasks and assignments
            3. **Decisions Made**: Important decisions and outcomes
            4. **Follow-ups**: Required follow-up actions
            5. **Strategic Insights**: Business implications
            6. **Risk Factors**: Any risks or concerns mentioned
            7. **Next Steps**: Recommended next actions
            
            Transcript:
            {transcript}
            
            Provide analysis in JSON format with these fields.
            """
            
            analysis_result = await ai_chain.analyze_text(
                text=transcript,
                analysis_type="meeting_summary",
                context="executive_meeting"
            )
            
            logger.info("Transcript analysis completed")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing transcript: {e}")
            return {
                "summary": "Analysis failed",
                "action_items": [],
                "decisions": [],
                "follow_ups": [],
                "insights": [],
                "risks": [],
                "next_steps": []
            }
    
    async def _update_meeting_record(self, transcript: str, analysis: Dict[str, Any]) -> None:
        """Update meeting record with transcript and analysis."""
        try:
            db_session = get_db_session()
            
            # Update meeting
            meeting = db_session.query(Meeting).filter(
                Meeting.id == self.current_meeting_id
            ).first()
            
            if meeting:
                meeting.end_time = datetime.now(timezone.utc)
                meeting.status = "completed"
                meeting.notes = analysis.get("summary", "")
                meeting.action_items = analysis.get("action_items", [])
                meeting.decisions = analysis.get("decisions", [])
                meeting.follow_up_required = len(analysis.get("follow_ups", [])) > 0
                
                # Create transcript record
                transcript_record = MeetingTranscript(
                    meeting_id=self.current_meeting_id,
                    transcript_text=transcript,
                    word_count=len(transcript.split()),
                    duration_minutes=30,  # TODO: Calculate actual duration
                    created_at=datetime.now(timezone.utc)
                )
                db_session.add(transcript_record)
                
                # Create analysis record
                analysis_record = MeetingAnalysis(
                    meeting_id=self.current_meeting_id,
                    analysis_data=analysis,
                    created_at=datetime.now(timezone.utc)
                )
                db_session.add(analysis_record)
                
                db_session.commit()
                logger.info("Meeting record updated with transcript and analysis")
            
            db_session.close()
            
        except Exception as e:
            logger.error(f"Error updating meeting record: {e}")
            raise
    
    def get_recording_status(self) -> Dict[str, Any]:
        """Get current recording status."""
        return {
            "is_recording": self.is_recording,
            "meeting_id": self.current_meeting_id,
            "frames_recorded": len(self.recording_frames),
            "duration_seconds": len(self.recording_frames) * self.config.chunk_size / self.config.sample_rate
        }
    
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.is_recording:
                self.is_recording = False
            
            self.audio.terminate()
            logger.info("Meeting recorder cleaned up")
            
        except Exception as e:
            logger.error(f"Error cleaning up recorder: {e}")


class MeetingManager:
    """Manages meeting recording and analysis workflows."""
    
    def __init__(self):
        self.recorder = MeetingRecorder()
        self.active_recordings = {}
    
    async def start_executive_meeting(
        self,
        meeting_title: str,
        attendees: List[str] = None,
        meeting_type: str = "executive"
    ) -> Dict[str, Any]:
        """Start recording an executive meeting."""
        try:
            meeting_id = f"meeting_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Start recording
            result = await self.recorder.start_recording(meeting_id, meeting_title)
            
            # Store active recording
            self.active_recordings[meeting_id] = {
                "title": meeting_title,
                "attendees": attendees or [],
                "type": meeting_type,
                "start_time": datetime.now(timezone.utc)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error starting executive meeting: {e}")
            raise
    
    async def end_executive_meeting(self, meeting_id: str) -> Dict[str, Any]:
        """End recording and analyze executive meeting."""
        try:
            if meeting_id not in self.active_recordings:
                raise ValueError(f"No active recording for meeting {meeting_id}")
            
            # Stop recording and process
            result = await self.recorder.stop_recording()
            
            # Remove from active recordings
            del self.active_recordings[meeting_id]
            
            return result
            
        except Exception as e:
            logger.error(f"Error ending executive meeting: {e}")
            raise
    
    async def get_meeting_summary(self, meeting_id: str) -> Dict[str, Any]:
        """Get summary of a completed meeting."""
        try:
            db_session = get_db_session()
            
            # Get meeting details
            meeting = db_session.query(Meeting).filter(
                Meeting.id == meeting_id
            ).first()
            
            if not meeting:
                raise ValueError(f"Meeting {meeting_id} not found")
            
            # Get transcript
            transcript = db_session.query(MeetingTranscript).filter(
                MeetingTranscript.meeting_id == meeting_id
            ).first()
            
            # Get analysis
            analysis = db_session.query(MeetingAnalysis).filter(
                MeetingAnalysis.meeting_id == meeting_id
            ).first()
            
            db_session.close()
            
            return {
                "meeting": {
                    "id": meeting.id,
                    "title": meeting.title,
                    "start_time": meeting.start_time,
                    "end_time": meeting.end_time,
                    "attendees": meeting.attendees,
                    "type": meeting.meeting_type,
                    "status": meeting.status
                },
                "transcript": {
                    "text": transcript.transcript_text if transcript else "",
                    "word_count": transcript.word_count if transcript else 0,
                    "duration_minutes": transcript.duration_minutes if transcript else 0
                },
                "analysis": analysis.analysis_data if analysis else {}
            }
            
        except Exception as e:
            logger.error(f"Error getting meeting summary: {e}")
            raise
    
    def get_active_meetings(self) -> List[Dict[str, Any]]:
        """Get list of currently active meetings."""
        return [
            {
                "meeting_id": meeting_id,
                **meeting_data
            }
            for meeting_id, meeting_data in self.active_recordings.items()
        ]
    
    def cleanup(self) -> None:
        """Clean up all resources."""
        self.recorder.cleanup()


# Global meeting manager instance
meeting_manager = MeetingManager()


def get_meeting_manager() -> MeetingManager:
    """Get the global meeting manager instance."""
    return meeting_manager 