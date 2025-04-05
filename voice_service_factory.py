"""
VoiceServiceFactory - Factory for creating voice service instances based on configuration
"""
from gtts_voice_service import GTTSVoiceService
from elevenlabs_voice_service import ElevenLabsVoiceService

class VoiceServiceFactory:
    @staticmethod
    def create(voice_engine="gtts", **kwargs):
        """
        Create a voice service instance based on the engine type and parameters
        
        Parameters:
        - voice_engine: "gtts" or "elevenlabs"
        - kwargs: Engine-specific parameters
        
        Returns:
        - A voice service instance
        """
        if voice_engine == "elevenlabs":
            api_key = kwargs.get("elevenlabs_api_key", "")
            if not api_key:
                raise ValueError("ElevenLabs requires an API key")
            return ElevenLabsVoiceService(
                api_key=api_key,
                voice_id=kwargs.get("elevenlabs_voice_id", "21m00Tcm4TlvDq8ikWAM"),
                model_id=kwargs.get("elevenlabs_model_id", "eleven_monolingual_v1"),
                stability=kwargs.get("elevenlabs_stability", 0.5),
                similarity_boost=kwargs.get("elevenlabs_similarity_boost", 0.5),
                sentence_buffer_size=kwargs.get("sentence_buffer_size", 3)
            )
        elif voice_engine == "gtts":
            return GTTSVoiceService(
                lang=kwargs.get("lang", "en"),
                slow=kwargs.get("slow", False),
                sentence_buffer_size=kwargs.get("sentence_buffer_size", 3)
            )
        else:
            raise ValueError("voice_engine must be 'gtts' or 'elevenlabs'")