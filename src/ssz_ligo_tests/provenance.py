"""Provenance tracking for all SSZ-LIGO tests."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class ProvenanceRecord:
    timestamp: str
    action: str
    source_file: str
    equation_name: str
    status: str
    notes: str


class ProvenanceLog:
    """Track all decisions about equations and tests."""
    
    def __init__(self):
        self.records: List[ProvenanceRecord] = []
    
    def log_equation_lock(self, equation_name: str, source_file: str, notes: str = ""):
        """Log when an equation is locked from corpus."""
        record = ProvenanceRecord(
            timestamp=datetime.now().isoformat(),
            action="EQUATION_LOCKED",
            source_file=source_file,
            equation_name=equation_name,
            status="LOCKED",
            notes=notes
        )
        self.records.append(record)
    
    def log_equation_missing(self, equation_name: str, notes: str = ""):
        """Log when an equation is found missing."""
        record = ProvenanceRecord(
            timestamp=datetime.now().isoformat(),
            action="EQUATION_MISSING",
            source_file="NOT_FOUND",
            equation_name=equation_name,
            status="MISSING",
            notes=notes
        )
        self.records.append(record)
    
    def log_test_blocked(self, test_name: str, reason: str):
        """Log when a test is blocked."""
        record = ProvenanceRecord(
            timestamp=datetime.now().isoformat(),
            action="TEST_BLOCKED",
            source_file="",
            equation_name=test_name,
            status="BLOCKED",
            notes=reason
        )
        self.records.append(record)
    
    def log_test_design(self, test_name: str, design_notes: str):
        """Log test design decisions."""
        record = ProvenanceRecord(
            timestamp=datetime.now().isoformat(),
            action="TEST_DESIGNED",
            source_file="",
            equation_name=test_name,
            status="DESIGNED",
            notes=design_notes
        )
        self.records.append(record)
    
    def export_markdown(self, filepath: str):
        """Export provenance log as markdown."""
        with open(filepath, 'w') as f:
            f.write("# Provenance Log\n\n")
            for record in self.records:
                f.write(f"## {record.timestamp}\n")
                f.write(f"**Action:** {record.action}\n")
                f.write(f"**Equation/Test:** {record.equation_name}\n")
                f.write(f"**Status:** {record.status}\n")
                f.write(f"**Source:** {record.source_file}\n")
                f.write(f"**Notes:** {record.notes}\n\n")


# Global provenance log
provenance = ProvenanceLog()
