# SmartOCR-RC

SmartOCR-RC is a comprehensive Optical Character Recognition (OCR) and data extraction pipeline designed to process document images efficiently. It leverages PaddleOCR for robust text detection and recognition, and integrates with local Large Language Models (LLMs) via Ollama to intelligently clean, structure, and extract JSON data from the raw OCR output.

## Features

- **Advanced OCR Processing:** Built on PaddleOCR, supporting custom parameters, angle classification, and CPU/GPU execution.
- **LLM Integration:** Uses local LLM models (e.g., Qwen, Llama 3.2) to process raw text into structured JSON data.
- **Batch Processing:** Automatically scans input directories and processes multiple images asynchronously.
- **Interactive UI:** A CustomTkinter-based dashboard for configuration, batch processing, and a detailed image viewer/inspector for validating and editing extracted data.
- **CLI Mode:** Capable of running entirely in the terminal for headless batch operations.

## Prerequisites

Before running SmartOCR-RC, ensure you have the following installed on your system:

1. **Python 3.8+**
2. **Ollama:** Installed and running locally. You will need to pull the models specified in your configuration (e.g., `qwen2.5:14b-instruct`, `llama3.2:3b`).
   ```bash
   ollama pull qwen2.5:14b-instruct
   ollama pull llama3.2:3b
   ```
3. (Optional) **CUDA Toolkit & cuDNN:** If you intend to use GPU acceleration for PaddleOCR.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd SmartOCR-RC
   ```

2. Create and activate a virtual environment (recommended):
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

The application uses a `config.json` file for settings. A template is provided as `config.example.json`. 

On the first run or via the GUI Dashboard, you can configure paths, OCR parameters, and LLM model selections. The configuration file will be automatically saved to the root directory.

## Usage

### GUI Mode

To launch the full graphical interface, run:
```bash
python main.py
```
From the dashboard, you can:
- Configure OCR and LLM settings.
- Launch the Batch Processing tool.
- Open the Image Viewer to inspect results, crop images, and correct extracted data.

### CLI Mode

To run a headless batch process on all images located in the configured `data/` directory, use the `--cli` flag:
```bash
python main.py --cli
```
Results will be output to the `output/` directory, including processed images, raw logs, and a consolidated `results.csv`.

## Project Structure

- `src/core/`: Core processing logic, including the OCR engine, LLM engine, and pipeline coordinator.
- `src/ui/`: CustomTkinter interface components (Dashboard, Viewer, Batch Window).
- `src/utils/`: Configuration management, logging, and image processing utilities.
- `data/`: Default input directory for images to be processed.
- `output/`: Default output directory for processed results and logs.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
