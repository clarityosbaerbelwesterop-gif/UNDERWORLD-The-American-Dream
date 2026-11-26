"""UNDERWORLD procedural audio pipeline (P6, T-AUD-01).

Every sound in the game is synthesized from code (numpy/scipy DSP): 100 % original, no third-party
samples, no licence questions, fully reproducible from a seed. `Tools/uwp build-audio` renders the
whole library to Ogg Vorbis under Assets/Audio/ and writes the runtime event table
GodotProject/Data/Content/audio.json that the AudioDirector autoload reads.
"""
