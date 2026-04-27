
---

### Download Vosk Model (vosk-model-small-en-us-0.15)

1. Go to the official Vosk models page:
   [https://alphacephei.com/vosk/models](https://alphacephei.com/vosk/models)

2. Download the model:

   * File name: `vosk-model-small-en-us-0.15.zip`

3. Extract the archive:

```bash
unzip vosk-model-small-en-us-0.15.zip
```

4. Move the extracted folder into your project directory:

```bash
mv vosk-model-small-en-us-0.15 ./models/
```

5. Final structure should look like:

```
project/
 ├── models/
 │    └── vosk-model-small-en-us-0.15/
 ├── main.py
```

6. Update your code/config if needed:

```python
MODEL_PATH = "models/vosk-model-small-en-us-0.15"
```

---

### Windows (No unzip command)

If you're on Windows:

* Right-click → **Extract All**
* Move the folder manually into `models/`

---

### Common Mistake (Fix This)

If your code throws “model not found”:

* You likely placed the **zip file**, not the extracted folder
* Or your path is wrong

Fix:

* Ensure folder contains files like `am`, `conf`, `graph`

---
