"""
sound_effects.py
Audio synthesizer trigger scripts for ZenSudoku (Web Audio API Bridge):

Audio Requirements & Balance:
1. Shared gain constant:
   SOUND_GAIN = { 'correct': 0.25, 'wrong': 0.25, 'erase': 0.12 }
2. Erase button: Realistic pencil scribbling on rough paper (250-400 ms), softer gain (0.12).
3. Wrong digit: Existing Erase sound (descending 320 Hz -> 80 Hz sine ramp), gain (0.25).
4. Correct digit: Short, soft, clean tick or pop (80-120 ms), clearly audible, gain (0.25).
5. Old wrong-input sound (sawtooth fart tone) is completely deleted.
6. NO sound for anything else (undo/redo, hints, notes, navigation).
7. Respects sound on/off setting.
"""

from typing import Dict, Optional

# Single shared constant for all sound gains
SOUND_GAIN: Dict[str, float] = {
    'correct': 0.25,
    'wrong': 0.25,
    'erase': 0.12,
}


class SoundManager:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    # Browser Web Audio JS synthesizer initialized once on the page
    WEB_AUDIO_JS = f"""
    (function() {{
        if (window.__zenSoundController) return;
        
        const SOUND_GAIN = {{
            correct: {SOUND_GAIN['correct']},
            wrong: {SOUND_GAIN['wrong']},
            erase: {SOUND_GAIN['erase']}
        }};
        
        class ZenAudioEngine {{
            constructor() {{
                this.ctx = null;
                this.enabled = true;
            }}
            
            initContext() {{
                if (!this.ctx) {{
                    const AudioCtx = window.AudioContext || window.webkitAudioContext;
                    if (AudioCtx) this.ctx = new AudioCtx();
                }}
                if (this.ctx && this.ctx.state === 'suspended') {{
                    this.ctx.resume().catch(() => {{}});
                }}
                return this.ctx;
            }}
            
            // Correct digit: Short, soft, clean tick/pop (80-120 ms)
            playCorrect() {{
                if (!this.enabled) return;
                const ctx = this.initContext();
                if (!ctx) return;
                
                try {{
                    const now = ctx.currentTime;
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    
                    osc.type = 'sine';
                    // Soft clean pop/tick (starts at 560 Hz, quickly drops to 240 Hz over 90ms)
                    osc.frequency.setValueAtTime(560, now);
                    osc.frequency.exponentialRampToValueAtTime(240, now + 0.09);
                    
                    gain.gain.setValueAtTime(0.0001, now);
                    gain.gain.linearRampToValueAtTime(SOUND_GAIN.correct, now + 0.008);
                    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.09);
                    
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    
                    osc.start(now);
                    osc.stop(now + 0.095);
                }} catch(e) {{}}
            }}
            
            // Erase Sound: Realistic pencil scribbling on rough paper with softer volume (SOUND_GAIN.erase = 0.12)
            playErase() {{
                if (!this.enabled) return;
                const ctx = this.initContext();
                if (!ctx) return;
                
                try {{
                    const duration = 0.30;
                    const bufferSize = Math.floor(ctx.sampleRate * duration);
                    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
                    const output = buffer.getChannelData(0);
                    
                    let b0 = 0, b1 = 0, b2 = 0;
                    for (let i = 0; i < bufferSize; i++) {{
                        const white = Math.random() * 2 - 1;
                        b0 = 0.99886 * b0 + white * 0.0555179;
                        b1 = 0.99332 * b1 + white * 0.0750759;
                        b2 = 0.96900 * b2 + white * 0.1538520;
                        output[i] = (b0 + b1 + b2) * 0.35;
                    }}
                    
                    const noise = ctx.createBufferSource();
                    noise.buffer = buffer;
                    
                    const bandpass = ctx.createBiquadFilter();
                    bandpass.type = 'bandpass';
                    bandpass.frequency.setValueAtTime(1600, ctx.currentTime);
                    bandpass.Q.setValueAtTime(2.0, ctx.currentTime);
                    
                    const gain = ctx.createGain();
                    const now = ctx.currentTime;
                    gain.gain.setValueAtTime(0.0001, now);
                    
                    // 3 quick friction strokes scaled to SOUND_GAIN.erase (0.12)
                    gain.gain.linearRampToValueAtTime(SOUND_GAIN.erase * 0.85, now + 0.03);
                    gain.gain.linearRampToValueAtTime(SOUND_GAIN.erase * 0.20, now + 0.09);
                    gain.gain.linearRampToValueAtTime(SOUND_GAIN.erase, now + 0.15);
                    gain.gain.linearRampToValueAtTime(SOUND_GAIN.erase * 0.25, now + 0.21);
                    gain.gain.linearRampToValueAtTime(SOUND_GAIN.erase * 0.70, now + 0.25);
                    gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);
                    
                    noise.connect(bandpass);
                    bandpass.connect(gain);
                    gain.connect(ctx.destination);
                    
                    noise.start(now);
                    noise.stop(now + duration);
                }} catch(e) {{}}
            }}
            
            // Wrong-digit action: Existing Erase sound (descending 320 Hz -> 80 Hz sine)
            playWrongDigit() {{
                if (!this.enabled) return;
                const ctx = this.initContext();
                if (!ctx) return;
                
                try {{
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    const now = ctx.currentTime;
                    
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(320, now);
                    osc.frequency.exponentialRampToValueAtTime(80, now + 0.14);
                    
                    gain.gain.setValueAtTime(SOUND_GAIN.wrong, now);
                    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.14);
                    
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    
                    osc.start(now);
                    osc.stop(now + 0.15);
                }} catch(e) {{}}
            }}
        }}
        
        window.__zenSoundController = new ZenAudioEngine();
    }})();
    """

    def get_sound_js(self, action: str) -> Optional[str]:
        if not self.enabled:
            return None
        if action == 'erase':
            return 'window.__zenSoundController && window.__zenSoundController.playErase();'
        elif action in ('wrong_digit', 'mistake', 'error'):
            # Wrong digit plays the existing erase sound
            return 'window.__zenSoundController && window.__zenSoundController.playWrongDigit();'
        elif action in ('correct', 'tick', 'pop'):
            # Correct digit plays the clean tick/pop
            return 'window.__zenSoundController && window.__zenSoundController.playCorrect();'
        # All other actions (undo, redo, hint, note, nav) are strictly silent
        return None


sounds = SoundManager(enabled=True)
