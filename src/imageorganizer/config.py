from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProcessorConfig:
    source: Path
    destination: Path
    ignore_duplicates: bool = False
    quiet: bool = False
    dry_run: bool = False

    def validate(self):
        """Check if paths are valid before starting the queue."""
        if not self.source.is_dir():
            return f"Error: {self.source} is not a valid directory."
        if not self.destination.is_dir():
            return f"Error: {self.destination} is not a valid directory."
        return None
