"""codegen - Assembly Code Generation backend for ToyLang.

Exports:
    AssemblyGenerator  - Translates ICG ThreeAddressInstructions to x86-64 NASM assembly.
    generate_assembly  - Convenience wrapper that accepts an icg_result dict.
"""

from .assembly_generator import AssemblyGenerator, generate_assembly

__all__ = ["AssemblyGenerator", "generate_assembly"]
