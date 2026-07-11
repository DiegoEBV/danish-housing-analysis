"""Configuración de pytest: garantiza que `src/` esté en el path para importar
`danish_housing` sin depender de la instalación del paquete ni de config externa.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
