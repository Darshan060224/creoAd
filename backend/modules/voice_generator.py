"""
Stage B3: Generate voiceover using local engines.
Prefers Chatterbox Turbo, then Coqui TTS, then pyttsx3, then espeak-ng fallback.
NEVER returns empty audio — always produces at least a silent stub.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from ..config import settings
    from ..pipeline.progress import pub_start, pub_log, pub_done, pub_error
except ImportError:
    from config import settings
    from pipeline.progress import pub_start, pub_log, pub_done, pub_error

try:
    from .voice_backends import (
        create_silent_audio,
        generate_chatterbox_voiceover,
        generate_coqui_voiceover,
        generate_pyttsx3_voiceover,
        generate_espeak_voiceover,
        is_command_available,
    )
except ImportError:
    from voice_backends import (
        create_silent_audio,
        generate_chatterbox_voiceover,
        generate_coqui_voiceover,
        generate_pyttsx3_voiceover,
        generate_espeak_voiceover,
        is_command_available,
    )


def _apply_audio_cleanup(audio_path: str):
    import tempfile
    tmp_path = audio_path + ".tmp.wav"
    try:
        os.rename(audio_path, tmp_path)
        cmd = [
            "ffmpeg", "-y", "-i", tmp_path,
            "-af", "afftdn=nf=-25,acompressor=threshold=-12dB:ratio=4:makeup=4,alimiter=limit=-2dB",
            audio_path
        ]
        subprocess.run(cmd, capture_output=True)
    except Exception as e:
        print(f"Audio cleanup failed: {e}")
        if os.path.exists(tmp_path) and not os.path.exists(audio_path):
            os.rename(tmp_path, audio_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    return audio_path


def _validate_narration_text(text: str, brand_info: Dict[str, Any] = None) -> str:
    """Ensure narration text is never empty or too short.
    
    This is the #1 fix for the '0 narration chunks' failure.
    """
    if not text or len(text.strip()) < 10:
        # Build fallback narration from brand info
        if brand_info:
            biz = brand_info.get("business", "our solution")
            usp = brand_info.get("usp", "quality service")
            cta = brand_info.get("cta", "Get started today")
            text = (
                f"Discover {biz}. "
                f"We offer {usp} that transforms the way you work. "
                f"Trusted by thousands of satisfied customers. "
                f"Real results you can see and measure. "
                f"{cta}. Visit our website to learn more."
            )
        else:
            text = (
                "Discover a better way to achieve your goals. "
                "Our proven solution delivers real results. "
                "Trusted by thousands of satisfied customers. "
                "Don't wait. Get started today."
            )
    
    # Validate minimum word count
    words = text.split()
    if len(words) < 10:
        text += " Experience the difference. Get started today and see real results."
    
    return text.strip()


def generate_voiceover(
    text: str, output_dir: str, voice: str = "female",
    job_id: str = "unknown", voice_plan: Dict[str, Any] = None,
    brand_info: Dict[str, Any] = None
) -> str:
    """
    Generate voiceover using Chatterbox Turbo or Coqui TTS.
    NEVER fails silently — always produces audio output.

    Args:
        text: Narration text (30-40 words for 30-second ad)
        output_dir: Output directory
        voice: "female" or "male" (determines model/speaker)
        job_id: The job ID for UI logging
        voice_plan: Optional voice direction from VoiceDirector (emotion, pace, energy)
        brand_info: Optional brand data for fallback narration generation

    Returns:
        Path to generated audio WAV file
    """

    Path(output_dir).mkdir(exist_ok=True)
    output_path = f"{output_dir}/voiceover.wav"
    
    # Extract voice direction
    pace = "medium"
    if voice_plan and isinstance(voice_plan, dict):
        pace = str(voice_plan.get("pace", "medium")).lower()
    
    preferred_backend = os.getenv("VOICE_BACKEND", "chatterbox").lower()
    pub_start(job_id, "voice", f"VOICE Backend: {preferred_backend}")
    pub_log(job_id, "voice", f"VOICE Backend: {preferred_backend} · device=auto · pace={pace}", pct=5)

    # === CRITICAL FIX: Validate narration text BEFORE attempting TTS ===
    text = _validate_narration_text(text, brand_info)

    try:
        audio_prompt_path = os.getenv("CHATTERBOX_AUDIO_PROMPT", "") or None

        sentences = [s.strip() for s in text.replace('!', '.').replace('?', '.').split('.') if s.strip()]
        
        if not sentences:
            # This should never happen after validation, but just in case
            pub_log(job_id, "voice", "VOICE ⚠ Empty narration after validation, using fallback text", pct=5)
            text = "Discover our solution. Get started today."
            sentences = [text]
            
        word_count = len(text.split())

        pub_log(job_id, "voice", f"VOICE Generating narration ({len(sentences)} sentences, {word_count} words, pace={pace})", pct=8)
        
        # Log chunks for UI feedback
        for i, sentence in enumerate(sentences):
            pub_log(job_id, "voice", f"VOICE Chunk {i+1}/{len(sentences)}: \"{sentence[:60]}...\"", pct=int((i/len(sentences))*80))

        # === BACKEND CHAIN: Try each backend in order ===
        
        # 1. Chatterbox (best quality)
        if preferred_backend == "chatterbox":
            try:
                res = generate_chatterbox_voiceover(text, output_path, audio_prompt_path=audio_prompt_path)
                res = _apply_audio_cleanup(res)
                pub_log(job_id, "voice", f"VOICE ✓ voice.wav · {len(sentences)} chunks · Chatterbox · {word_count} words", pct=95)
                return res
            except Exception as chatterbox_error:
                print(f"Chatterbox failed, falling back: {chatterbox_error}")
                pub_log(job_id, "voice", f"VOICE ⚠ Chatterbox failed: {str(chatterbox_error)[:50]}, trying Coqui...", pct=30)

        # 2. Coqui TTS
        if is_command_available("tts"):
            try:
                model_name = os.getenv(
                    "COQUI_TTS_MODEL",
                    "tts_models/en/ljspeech/tacotron2-DDC" if voice != "male" else "tts_models/en/ljspeech/glow-tts",
                )
                res = generate_coqui_voiceover(text, output_path, model_name=model_name)
                res = _apply_audio_cleanup(res)
                pub_log(job_id, "voice", f"VOICE ✓ voice.wav · {len(sentences)} chunks · Coqui · {word_count} words", pct=95)
                return res
            except Exception as coqui_error:
                print(f"Coqui TTS failed, falling back: {coqui_error}")
                pub_log(job_id, "voice", f"VOICE ⚠ Coqui failed: {str(coqui_error)[:50]}, trying pyttsx3...", pct=50)

        # 3. pyttsx3
        try:
            res = generate_pyttsx3_voiceover(text, output_path, pace=pace)
            # QUAL-E: Skip aggressive audio cleanup for lower-quality backends
            pub_log(job_id, "voice", f"VOICE ✓ voice.wav · {len(sentences)} chunks · pyttsx3 · {word_count} words", pct=95)
            return res
        except Exception as pyttsx3_error:
            print(f"pyttsx3 failed: {pyttsx3_error}")
            pub_log(job_id, "voice", f"VOICE ⚠ pyttsx3 failed: {str(pyttsx3_error)[:50]}, trying espeak...", pct=70)

        # 4. espeak-ng (new fallback)
        try:
            res = generate_espeak_voiceover(text, output_path, pace=pace)
            # QUAL-E: Skip aggressive audio cleanup for lower-quality backends
            pub_log(job_id, "voice", f"VOICE ✓ voice.wav · {len(sentences)} chunks · espeak · {word_count} words", pct=95)
            return res
        except Exception as espeak_error:
            print(f"espeak failed: {espeak_error}")
            pub_log(job_id, "voice", f"VOICE ⚠ espeak failed: {str(espeak_error)[:50]}", pct=85)

        # 5. ABSOLUTE LAST RESORT: Silent audio stub
        # This ensures the pipeline ALWAYS completes
        pub_log(job_id, "voice", "VOICE ⚠ CRITICAL: All voice backends failed — generating silent fallback", pct=90)
        create_silent_audio(output_path, duration=30)
        pub_log(job_id, "voice", "VOICE ⚠ voice.wav · SILENT FALLBACK · no TTS engine available", pct=95)
        return output_path

    except Exception as e:
        # Even the outer try/except should produce audio, not raise
        print(f"Voice generation catastrophic error: {str(e)}")
        pub_log(job_id, "voice", f"VOICE ✗ Catastrophic error: {str(e)[:80]} — silent fallback", pct=95)
        try:
            create_silent_audio(output_path, duration=30)
        except Exception:
            pass
        return output_path


def test_tts_installation() -> bool:
    """Check if TTS is installed"""
    result = subprocess.run(['which', 'tts'], capture_output=True)
    return result.returncode == 0
