import os
import sys
import logging
import torch
from docling.document_converter import (
    DocumentConverter as DoclingConverter, 
    PdfFormatOption, 
    ImageFormatOption, 
    WordFormatOption, 
    PowerpointFormatOption, 
    HTMLFormatOption,
    AudioFormatOption  # Import specifically for audio
)
from docling.datamodel.base_models import InputFormat
from docling.backend.docling_parse_v4_backend import DoclingParseV4DocumentBackend
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions, 
    AcceleratorOptions, 
    AcceleratorDevice,
    PipelineOptions,
    AsrPipelineOptions
)
from docling.pipeline.asr_pipeline import AsrPipeline

logger = logging.getLogger(__name__)
IS_MAC = (sys.platform == "darwin")

class DocumentConverter:
    def __init__(self):
        # Hardware acceleration
        accel_device = AcceleratorDevice.MPS if IS_MAC else (AcceleratorDevice.CUDA if torch.cuda.is_available() else AcceleratorDevice.CPU)
        accel = AcceleratorOptions(num_threads=4, device=accel_device)
        
        pdf_pipe = PdfPipelineOptions()
        pdf_pipe.accelerator_options = accel
        pdf_pipe.do_ocr = True 
        
        shared_pipe = PipelineOptions(accelerator_options=accel)
        asr_pipe = AsrPipelineOptions(accelerator_options=accel)
        
        docling_format_options = {}

        def register_format(name, option):
            fmt = getattr(InputFormat, name, None)
            if fmt:
                docling_format_options[fmt] = option

        # Register PDF with explicit backend
        register_format("PDF", PdfFormatOption(
            backend=DoclingParseV4DocumentBackend, 
            pipeline_options=pdf_pipe
        ))
        # Other formats
        register_format("IMAGE", ImageFormatOption(pipeline_options=shared_pipe))
        register_format("DOCX", WordFormatOption(pipeline_options=shared_pipe))
        register_format("PPTX", PowerpointFormatOption(pipeline_options=shared_pipe))
        register_format("HTML", HTMLFormatOption(pipeline_options=shared_pipe))

        # Register Audio correctly
        if IS_MAC:
            asr_opt = AudioFormatOption(
                pipeline_cls=AsrPipeline, 
                pipeline_options=asr_pipe
            )
            register_format("WAV", asr_opt)
            register_format("MP3", asr_opt)
            register_format("AUDIO", asr_opt)

        self.converter = DoclingConverter(format_options=docling_format_options)

    def convert_to_obj(self, abs_path: str):
        if not os.path.isabs(abs_path):
            abs_path = os.path.abspath(abs_path)
        return self.converter.convert(abs_path).document
