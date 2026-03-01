# SmartOCR-RC (Ration Card Processor)

SmartOCR-RC is a specialized Optical Character Recognition (OCR) and data extraction pipeline engineered specifically for processing **Indian Ration Cards**. It handles the complexities of low-quality scans, and non-standardized document formats by combining the robustness of PaddleOCR with the intelligence of local Large Language Models (LLMs).

This tool bridges the gap between unstructured, noisy physical documents and clean, structured digital databases (JSON/CSV) securely and locally.

## How It Works

The pipeline is orchestrated through a multi-engine architecture.

### Why This Architecture?

* On limited local hardware, LLM-based OCR models that directly process images are extremely slow.
* Loop-based control tests show that a single small local model becomes overwhelmed when forced to handle all tasks at once, causing reliability to drop to nearly unusable levels.
* Document images captured via mobile cameras often contain large amounts of white space and non-relevant regions, which degrade OCR accuracy if processed directly.

To address these constraints, the pipeline deliberately separates OCR, reasoning, and formatting into independent stages, each optimized for speed, accuracy, and reliability.

### Pipeline Overview

1. **Fast OCR-based image cleanup and text extraction.**
2. **LLM-based reasoning and data cleaning on raw OCR output.**
3. **Lightweight JSON normalization using a small local model.**

This multi-stage design avoids overloading a single model while maintaining high accuracy and predictable output.

### 1. Fast & Accurate OCR (PaddleOCR)

Images are first passed through a fast-scan OCR phase to crop out white space and non-relevant regions. Mobile-captured document images often include large margins around the actual document content. This step isolates the region of interest, significantly improving performance and accuracy in later stages.

A secondary, high-accuracy OCR pass extracts raw text while capturing bounding boxes to preserve spatial relationships (visual anchors).

### 2. Intelligent Data Extraction (Local LLMs via Ollama)

Instead of relying on rigid regex patterns—which fail on highly variable Indian ration cards—the raw OCR text and spatial data are passed to a local LLM (e.g., `qwen2.5:14b-instruct`). A carefully tested prompt provides explicit instructions about what to extract from noisy OCR output.

The LLM acts as a cleaning and reasoning agent, interpreting messy text to accurately identify names, family members, addresses, and card numbers. It produces a structured, JSON-like output.

A secondary, smaller LLM (e.g., `llama3.2:3b`) converts this cleaned output into strict, predictable JSON. Since the upstream model already produces an almost-JSON structure, this step runs extremely fast and achieves near-perfect accuracy (≈1 error in 5,000 loop-based tests).

### Why the Multi-Model Separation Works

* The initial PaddleOCR pass is extremely fast—it only detects the position of the first and last characters to draw a bounding box around the relevant portion of the image.
* By removing unrelated regions, the image does not need aggressive downscaling to fit the OCR model. PaddleOCR processes characters at higher effective resolution, improving raw text accuracy.
* During the cleaning stage, the raw text size is small (≈200 characters), and the output is even smaller. The reasoning LLM operates on minimal context and only needs to follow a detailed instruction prompt, making a lower-mid size instruction-following model (`qwen2.5:14b-instruct`) sufficient and stable.
* The final formatting step receives a small, clean JSON-like string and performs no complex reasoning. The small model (`llama3.2:3b`) therefore runs extremely fast and consistently.

Overall, this multi-model pipeline delivers significantly better accuracy, speed, and reliability than a single large-model approach on local hardware.

## Features

- **Built for Indian Document Complexities:** Designed to handle the unique formatting, varied typography, and physical wear-and-tear typical of Indian Ration Cards.
- **100% Local & Private:** All processing, from image recognition to LLM inference, happens locally on your machine. No sensitive demographic data is sent to cloud APIs.
- **Two-Stage AI Pipeline:** Uses a heavy "thinking" model for extraction and a lightweight model for JSON formatting, optimizing both accuracy and speed.
- **Interactive Validation UI:** A robust `CustomTkinter` interface that allows human operators to:
    *   Inspect the original image alongside the extracted data.
    *   Use a zoomable canvas to read fine print.
    *   Manually edit, correct, or force AI re-processing on specific fields.
    *   Auto-crop images based on detected text bounds.
- **Batch Processing:** Automatically scans input directories and processes hundreds of images asynchronously, saving results to a unified CSV.
- **Graceful Degradation:** The GUI remains fully functional even if OCR or LLM dependencies are temporarily missing or downloading.

## Prerequisites

Before running SmartOCR-RC, ensure you have the following installed on your system:

1. **Python 3.8+**
2. **Ollama:** Installed and running locally. You will need to pull the models specified in your configuration. The application will attempt to download these automatically if permitted, but manual installation is recommended:
   ```bash
   ollama pull qwen2.5:14b-instruct
   ollama pull llama3.2:3b
   ```
3. (Optional) **CUDA Toolkit & cuDNN:** Highly recommended for GPU acceleration with PaddleOCR and Ollama.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd SmartOCR-RC
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # On Windows
   .venv\Scripts\activate
   # On Linux/macOS
   source .venv/bin/activate
   ```

3. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

The application uses a `config.json` file. A template is provided as `config.example.json`.

You can configure paths, OCR confidence thresholds, CPU thread counts, and LLM model selections directly through the GUI Dashboard or by manually creating a `config.json` in the root directory.

## Usage

### GUI Mode (Interactive Validation & Setup)

To launch the full graphical interface (Dashboard, Batch Processor, Image Viewer), run:
```bash
python main.py
```
*Note: The application will automatically start the Ollama service in the background if it is not already running, and will safely shut it down upon exit.*

### CLI Mode (Headless Batching)

To run a headless batch process on all images located in the configured `data/` directory, use the `--cli` flag:
```bash
python main.py --cli
```
Results are saved to the `output/` directory, which includes:
- Cropped/processed images.
- Raw text and LLM reasoning logs (`output/logs/`).
- A consolidated `results.csv` containing all structured demographic data.

## Project Architecture

- `src/core/`: Contains the business logic.
  - `ocr_engine.py`: Wraps PaddleOCR for two-stage scanning.
  - `llm_engine.py`: Manages Ollama subprocesses, model lifecycle, and prompt execution.
  - `coordinator.py`: The central nervous system linking OCR outputs to LLM inputs.
- `src/ui/`: The CustomTkinter graphical interface.
  - `dashboard.py`: Central hub and settings manager.
  - `image_viewer.py`: The human-in-the-loop validation tool.
- `src/utils/`: Handlers for logging, image manipulation (cropping/rotating), and configuration state.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
