# Third-Party Software Licenses（第三方軟體授權）

本文件列出 AccomPartner 所使用的所有第三方開源套件及其授權資訊。  
This document lists all third-party open-source libraries used in AccomPartner and their respective license information.

---

## Backend Dependencies（Python）

| 套件 | 版本限制 | 授權 |
|------|---------|------|
| FastAPI | ≥ 0.111.0 | MIT |
| Uvicorn | ≥ 0.29.0 | BSD 3-Clause |
| Pydantic / Pydantic-Settings | ≥ 2.2.0 | MIT |
| SlowAPI | ≥ 0.1.9 | MIT |
| python-multipart | ≥ 0.0.9 | Apache 2.0 |
| Mido | ≥ 1.3.2 | MIT |
| python-dotenv | ≥ 1.0.0 | BSD 3-Clause |
| PyTorch (torch) | ≥ 2.0.0 | BSD 3-Clause |
| Symusic | ≥ 0.5.0 | MIT |
| MidiTok | ≥ 3.0.0 | MIT |
| Music21 | ≥ 9.0.0 | BSD 3-Clause |

---

## Frontend Dependencies（JavaScript / Node.js）

| 套件 | 版本限制 | 授權 |
|------|---------|------|
| Vue 3 | ^3.5.29 | MIT |
| Pinia | ^3.0.4 | MIT |
| Vite | ^7.3.1 | MIT |
| @vitejs/plugin-vue | ^6.0.4 | MIT |
| Tone.js | ^15.1.22 | MIT |
| @tonejs/midi | ^2.0.28 | MIT |
| VexFlow | ^5.0.0 | MIT |
| @huggingface/transformers | ^3.8.1 | Apache 2.0 |
| html-midi-player | ^1.6.0 | Apache 2.0 |
| midi-writer-js | ^3.2.1 | MIT |
| opensheetmusicdisplay | ^1.9.7 | MIT |
| Prettier | 3.8.1 | MIT |
| vite-plugin-vue-devtools | ^8.0.6 | MIT |

---

## License Texts（授權條款全文）

### MIT License

```
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

適用套件：FastAPI, Pydantic / Pydantic-Settings, SlowAPI, Mido, Symusic, MidiTok, Vue 3, Pinia, Vite, @vitejs/plugin-vue, Tone.js, @tonejs/midi, VexFlow, midi-writer-js, opensheetmusicdisplay, Prettier, vite-plugin-vue-devtools

---

### BSD 3-Clause License

```
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
```

適用套件：Uvicorn, PyTorch (torch), python-dotenv, Music21

---

### Apache License 2.0

```
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

適用套件：python-multipart, @huggingface/transformers, html-midi-player

---

## 訓練資料（Training Data）

### POP909 Dataset

- **用途**：本專案的 Transformer 伴奏模型以此資料集訓練。
- **授權**：僅限**非商業及學術研究**用途。使用者若將本專案或衍生模型用於任何商業目的，必須自行確認訓練資料的授權合規性。
- **引用**：
  > Wang Z, Chen K, Jiang J, et al. *POP909: A Pop-song Dataset for Music Arrangement Generation*. ISMIR 2020.
- **原始連結**：https://github.com/music-x-lab/POP909-Dataset

---

## 音訊取樣（Audio Samples）

| 取樣素材 | 來源 | 授權 |
|---------|------|------|
| Salamander Grand Piano | [`tonejs.github.io/audio/salamander/`](https://tonejs.github.io/audio/salamander/) | Creative Commons Attribution 3.0 |
| Acoustic Drum Kit | [`tonejs.github.io/audio/drum-samples/`](https://tonejs.github.io/audio/drum-samples/) | 由 Tone.js 提供，適用 MIT License |

> Salamander Grand Piano 使用的 CC BY 3.0 授權要求在分發時保留原始版權聲明。
> 原始作者：Alexander Holm。

---

*最後更新：2026-04-04*
