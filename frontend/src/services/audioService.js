// src/services/audioService.js
import * as Tone from 'tone'

class AudioService {
    constructor() {
        this.isReady = false;
        this.isLoading = false;
        
        // Synths
        this.melodySynth = null;
        this.accSynth = null;
        this.delSynth = null;
        this.metronome = null;
        this.kickSynth = null;
        this.snareSynth = null;
        this.hatSynth = null;
    }

    async init() {
        if (this.isReady || this.isLoading) return;
        this.isLoading = true;

        try {
            await Tone.start();
            
            const pianoUrls = { 
                C3: 'C3.mp3', 'F#3': 'Fs3.mp3', 
                C4: 'C4.mp3', 'F#4': 'Fs4.mp3', 
                C5: 'C5.mp3' 
            };
            const baseUrl = 'https://tonejs.github.io/audio/salamander/';

            // 1. 主旋律鋼琴 (音量稍大)
            this.melodySynth = new Tone.Sampler({ urls: pianoUrls, baseUrl }).toDestination();
            this.melodySynth.volume.value = 2;

            // 2. 伴奏鋼琴 (音量稍小，避免蓋過主旋律)
            this.accSynth = new Tone.Sampler({ urls: pianoUrls, baseUrl }).toDestination();
            this.accSynth.volume.value = -3;

            // 3. 刪除音符的音效
            this.delSynth = new Tone.MembraneSynth().toDestination();
            this.delSynth.volume.value = -15;

            // 4. 節拍器 (Beep)
            this.metronome = new Tone.Synth({ 
                oscillator: { type: 'square' }, 
                envelope: { attack: 0.001, decay: 0.05, sustain: 0, release: 0.01 } 
            }).toDestination();
            this.metronome.volume.value = -12;

            // 5. 高品質真鼓組取樣器 (分軌實作以方便混音)
            const drumBaseUrl = 'https://tonejs.github.io/audio/drum-samples/acoustic-kit/';
            
            this.kickSamp = new Tone.Sampler({ urls: { A1: 'kick.mp3' }, baseUrl: drumBaseUrl }).toDestination();
            this.snareSamp = new Tone.Sampler({ urls: { B1: 'snare.mp3' }, baseUrl: drumBaseUrl }).toDestination();
            this.hatSamp = new Tone.Sampler({ urls: { C2: 'hihat.mp3' }, baseUrl: drumBaseUrl }).toDestination();

            // 預設平衡：鈸聲必須顯著低於大鼓與小鼓
            this.kickSamp.volume.value = -6;
            this.snareSamp.volume.value = -6;
            this.hatSamp.volume.value = -22; 
            
            this.kickSynth = { 
                triggerAttack: (t) => {
                    console.log("🥁 Kick [Attack] Triggered at:", t);
                    this.kickSamp.triggerAttack('A1', t);
                },
                triggerAttackRelease: (a1, a2, a3) => {
                    const time = (a3 !== undefined) ? a3 : a2;
                    this.kickSamp.triggerAttack('A1', time);
                },
                volume: this.kickSamp.volume
            };
            this.snareSynth = { 
                triggerAttack: (t) => {
                    console.log("🥁 Snare [Attack] Triggered at:", t);
                    this.snareSamp.triggerAttack('B1', t);
                },
                triggerAttackRelease: (a1, a2, a3) => {
                    const time = (a3 !== undefined) ? a3 : a2;
                    console.log("🥁 Snare [Release] Triggered at (time):", time);
                    this.snareSamp.triggerAttack('B1', time);
                },
                volume: this.snareSamp.volume
            };
            this.hatSynth = { 
                triggerAttack: (t) => {
                    this.hatSamp.triggerAttack('C2', t);
                },
                triggerAttackRelease: (a1, a2, a3) => {
                    const time = (a3 !== undefined) ? a3 : a2;
                    this.hatSamp.triggerAttack('C2', time);
                },
                volume: this.hatSamp.volume
            };

            await Tone.loaded();
            this.isReady = true;
            console.log("✅ 全域音訊引擎與高品質取樣器載入完成！");
            console.log("🎹 鋼琴取樣器狀態:", this.melodySynth.loaded ? "已就緒" : "等待中");
            console.log("🥁 鼓組分軌取樣狀態: 已完成平衡校準");
        } catch (error) {
            console.error("❌ 音訊引擎載入失敗:", error);
        } finally {
            this.isLoading = false;
        }
    }

    // 全域停止播放方法
    stopAll() {
        Tone.Transport.stop();
        Tone.Transport.cancel();
        if (this.melodySynth) this.melodySynth.releaseAll();
        if (this.accSynth) this.accSynth.releaseAll();
        // 鼓組也需停止
        if (this.kickSamp) this.kickSamp.releaseAll();
        if (this.snareSamp) this.snareSamp.releaseAll();
        if (this.hatSamp) this.hatSamp.releaseAll();
    }
}

export const audioService = new AudioService();
export default audioService;