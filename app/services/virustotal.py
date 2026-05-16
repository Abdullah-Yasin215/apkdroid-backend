"""VirusTotal API integration for APK scanning and safety badges"""

import aiohttp
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models import VirusScan, APKVersion

logger = logging.getLogger(__name__)
settings = get_settings()


class VirusTotalClient:
    """Client for VirusTotal API integration"""
    
    def __init__(self):
        self.base_url = "https://www.virustotal.com/api/v3"
        self.api_key = getattr(settings, 'VIRUSTOTAL_API_KEY', None)
        if not self.api_key:
            logger.warning("VirusTotal API key not configured")
    
    @property
    def headers(self) -> Dict[str, str]:
        """Get authorization headers for VirusTotal API"""
        return {
            "x-apikey": self.api_key,
            "Accept": "application/json"
        }
    
    async def get_file_report(self, file_hash: str, hash_type: str = "sha256") -> Optional[Dict]:
        """
        Get existing file report from VirusTotal.
        
        Args:
            file_hash: SHA256, SHA1, or MD5 hash of the file
            hash_type: Type of hash ('sha256', 'sha1', 'md5')
        
        Returns:
            File report data or None if not found
        """
        if not self.api_key:
            logger.warning("VirusTotal API key not configured, skipping scan")
            return None
        
        try:
            url = f"{self.base_url}/files/{file_hash}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("data", {})
                    elif resp.status == 404:
                        logger.info(f"File {file_hash} not found in VirusTotal")
                        return None
                    else:
                        logger.error(f"VirusTotal API error: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching VirusTotal report: {str(e)}")
            return None
    
    async def submit_file_url(self, file_url: str) -> Optional[Dict]:
        """
        Submit a file URL for scanning.
        
        Args:
            file_url: Direct URL to the file
        
        Returns:
            Scan submission data or None on error
        """
        if not self.api_key:
            return None
        
        try:
            url = f"{self.base_url}/urls"
            
            data = {"url": file_url}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=self.headers, data=data, 
                                      timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("data", {})
                    else:
                        logger.error(f"VirusTotal submission error: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"Error submitting to VirusTotal: {str(e)}")
            return None
    
    def parse_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse VirusTotal report into our format.
        
        Args:
            report: VirusTotal file report
        
        Returns:
            Parsed scan data
        """
        try:
            attributes = report.get("attributes", {})
            last_analysis_stats = attributes.get("last_analysis_stats", {})
            last_analysis_results = attributes.get("last_analysis_results", {})
            
            malicious_count = last_analysis_stats.get("malicious", 0)
            suspicious_count = last_analysis_stats.get("suspicious", 0)
            undetected_count = last_analysis_stats.get("undetected", 0)
            total_vendors = sum(last_analysis_stats.values())
            
            # Determine safety badge
            if malicious_count > 0:
                safety_badge = "malware"
            elif suspicious_count > 0:
                safety_badge = "suspicious"
            elif malicious_count == 0 and total_vendors > 0:
                safety_badge = "safe"
            else:
                safety_badge = "unknown"
            
            return {
                "malicious_count": malicious_count,
                "suspicious_count": suspicious_count,
                "undetected_count": undetected_count,
                "total_vendors": total_vendors,
                "safety_badge": safety_badge,
                "vendor_results": last_analysis_results,
                "scan_date": datetime.utcnow(),
                "vt_permalink": report.get("links", {}).get("self", ""),
            }
        except Exception as e:
            logger.error(f"Error parsing VirusTotal report: {str(e)}")
            return {
                "malicious_count": 0,
                "suspicious_count": 0,
                "undetected_count": 0,
                "total_vendors": 0,
                "safety_badge": "unknown",
                "scan_date": datetime.utcnow(),
            }


async def scan_apk_version(
    version_id: str,
    file_url: str,
    file_hash: Optional[str] = None,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Scan an APK version and store results.
    
    Args:
        version_id: APKVersion ID
        file_url: URL to the APK file
        file_hash: Optional pre-computed SHA256 hash
        db: Database session
    
    Returns:
        Scan results
    """
    client = VirusTotalClient()
    
    # Use provided hash or fetch from VirusTotal by URL
    vt_report = None
    
    if file_hash:
        # Try to get existing report by hash
        vt_report = await client.get_file_report(file_hash, "sha256")
    
    if not vt_report:
        # Submit URL for scanning
        submission = await client.submit_file_url(file_url)
        if submission:
            logger.info(f"Submitted {file_url} for VirusTotal scanning")
    
    # Parse results
    if vt_report:
        scan_data = client.parse_report(vt_report)
    else:
        scan_data = {
            "malicious_count": 0,
            "suspicious_count": 0,
            "undetected_count": 0,
            "total_vendors": 0,
            "safety_badge": "pending",
            "scan_date": datetime.utcnow(),
        }
    
    # Store in database if provided
    if db and version_id:
        try:
            from sqlalchemy.dialects.postgresql import UUID as PG_UUID
            
            # Create or update scan record
            scan = db.query(VirusScan).filter(
                VirusScan.version_id == version_id
            ).first()
            
            if not scan:
                scan = VirusScan(
                    version_id=version_id,
                    file_hash=file_hash or "unknown"
                )
            
            scan.malicious_count = scan_data["malicious_count"]
            scan.suspicious_count = scan_data["suspicious_count"]
            scan.undetected_count = scan_data["undetected_count"]
            scan.total_vendors = scan_data["total_vendors"]
            scan.safety_badge = scan_data["safety_badge"]
            scan.scan_date = scan_data["scan_date"]
            scan.vendor_results = scan_data.get("vendor_results")
            scan.vt_permalink = scan_data.get("vt_permalink")
            
            db.add(scan)
            db.commit()
        except Exception as e:
            logger.error(f"Error storing VirusTotal scan: {str(e)}")
    
    return scan_data


def calculate_sha256(file_path: str) -> str:
    """Calculate SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()
