# SmartOCR-RC (Ration Card Processor)

SmartOCR-RC is a specialized Optical Character Recognition (OCR) and data extraction pipeline engineered specifically for processing **Indian Ration Cards**. It handles the complexities of low-quality scans, regional languages, and non-standardized document formats by combining the robustness of PaddleOCR with the intelligence of local Large Language Models (LLMs).

This tool bridges the gap between unstructured, noisy physical documents and clean, structured digital databases (JSON/CSV) securely and locally.

## How It Works

The pipeline is orchestrated through a dual-engine architecture:

1.  **Fast & Accurate OCR (PaddleOCR):**
    *   Images are first passed through a fast-scan OCR phase to determine orientation and general layout.
    *   A secondary, highly-accurate OCR pass extracts raw text, capturing bounding boxes to maintain spatial relationships (visual anchors).
2.  **Intelligent Data Extraction (Local LLMs via Ollama):**
    *   Instead of relying on rigid Regex patterns (which fail on highly variable Indian ration cards), the raw text and spatial data are passed to a local LLM (e.g., `qwen2.5:14b-instruct`).
    *   The LLM acts as a "cleaning" and "reasoning" agent, interpreting the messy OCR output to accurately identify names, family members, addresses, and card numbers.
    *   A secondary, smaller LLM (e.g., `llama3.2:3b`) formats this cleaned data into strict, predictable JSON.

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
