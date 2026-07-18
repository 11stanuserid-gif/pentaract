# =============================================================================
# REPORT GENERATOR
# Generates comprehensive HTML reports of security test results
# =============================================================================

import json
import logging
import os
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates comprehensive HTML reports from test results."""

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(self, results: Dict) -> str:
        """
        Generate HTML report from test results.

        Returns:
            Path to the generated HTML report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(self.output_dir, f"security_report_{timestamp}.html")

        html_content = self._build_html(results)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"Report generated: {report_path}")
        return report_path

    def _build_html(self, results: Dict) -> str:
        """Build the complete HTML report."""
        meta = results["test_metadata"]
        signup = results["signup_summary"]
        score = results["security_score"]
        breakdown = results["test_breakdown"]
        attempts = results["attempts"]
        recommendations = results["recommendations"]

        # Determine overall status color
        if score["overall_percentage"] >= 70:
            status_color = "#27ae60"  # Green
            status_text = "GOOD"
        elif score["overall_percentage"] >= 40:
            status_color = "#f39c12"  # Orange
            status_text = "MODERATE"
        else:
            status_color = "#e74c3c"  # Red
            status_text = "CRITICAL"

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Signup Shield Audit Report - {meta['target_url']}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            line-height: 1.6;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 30px 20px;
        }}

        /* Header */
        .header {{
            text-align: center;
            padding: 40px 0;
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border-radius: 16px;
            margin-bottom: 30px;
            border: 1px solid #334155;
            position: relative;
            overflow: hidden;
        }}

        .header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899);
        }}

        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #60a5fa, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .header .subtitle {{
            color: #94a3b8;
            font-size: 1.1em;
        }}

        .header .timestamp {{
            color: #64748b;
            font-size: 0.9em;
            margin-top: 10px;
        }}

        /* Score Card */
        .score-card {{
            background: linear-gradient(135deg, #1e293b, #334155);
            border-radius: 16px;
            padding: 30px;
            text-align: center;
            margin-bottom: 30px;
            border: 1px solid #475569;
        }}

        .score-circle {{
            width: 150px;
            height: 150px;
            border-radius: 50%;
            background: conic-gradient({status_color} {score['overall_percentage'] * 3.6}deg, #334155 0deg);
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px;
            position: relative;
        }}

        .score-circle::before {{
            content: '';
            width: 120px;
            height: 120px;
            border-radius: 50%;
            background: #1e293b;
            position: absolute;
        }}

        .score-value {{
            position: relative;
            z-index: 1;
            font-size: 2.5em;
            font-weight: bold;
            color: {status_color};
        }}

        .score-label {{
            font-size: 1.2em;
            color: {status_color};
            font-weight: bold;
            margin-bottom: 5px;
        }}

        .score-sublabel {{
            color: #94a3b8;
            font-size: 0.9em;
        }}

        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .stat-card {{
            background: #1e293b;
            border-radius: 12px;
            padding: 24px;
            border: 1px solid #334155;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .stat-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }}

        .stat-icon {{
            font-size: 2em;
            margin-bottom: 12px;
        }}

        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #f1f5f9;
            margin-bottom: 4px;
        }}

        .stat-label {{
            color: #94a3b8;
            font-size: 0.9em;
        }}

        /* Section */
        .section {{
            background: #1e293b;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            border: 1px solid #334155;
        }}

        .section-title {{
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 2px solid #334155;
            color: #e2e8f0;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        /* Test Results */
        .test-item {{
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 12px;
            border-left: 4px solid;
            background: #0f172a;
        }}

        .test-pass {{
            border-color: #27ae60;
        }}

        .test-fail {{
            border-color: #e74c3c;
        }}

        .test-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}

        .test-name {{
            font-weight: bold;
            font-size: 1.05em;
        }}

        .test-badge {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
        }}

        .badge-pass {{
            background: rgba(39, 174, 96, 0.2);
            color: #2ecc71;
        }}

        .badge-fail {{
            background: rgba(231, 76, 60, 0.2);
            color: #e74c3c;
        }}

        .test-details {{
            color: #94a3b8;
            font-size: 0.9em;
            line-height: 1.5;
        }}

        .test-details ul {{
            margin: 8px 0 0 20px;
        }}

        .test-details li {{
            margin-bottom: 4px;
        }}

        /* Recommendations */
        .recommendation {{
            padding: 14px 16px;
            border-radius: 8px;
            margin-bottom: 10px;
            font-size: 0.95em;
            line-height: 1.5;
        }}

        .rec-critical {{
            background: rgba(231, 76, 60, 0.15);
            border-left: 4px solid #e74c3c;
            color: #f1948a;
        }}

        .rec-high {{
            background: rgba(230, 126, 34, 0.15);
            border-left: 4px solid #e67e22;
            color: #f0b27a;
        }}

        .rec-medium {{
            background: rgba(241, 196, 15, 0.15);
            border-left: 4px solid #f1c40f;
            color: #f9e79f;
        }}

        .rec-low {{
            background: rgba(52, 152, 219, 0.15);
            border-left: 4px solid #3498db;
            color: #85c1e9;
        }}

        .rec-good {{
            background: rgba(39, 174, 96, 0.15);
            border-left: 4px solid #27ae60;
            color: #82e0aa;
        }}

        /* Attempts Table */
        .attempts-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 16px;
        }}

        .attempts-table th {{
            background: #334155;
            padding: 12px;
            text-align: left;
            font-weight: bold;
            color: #e2e8f0;
            border-bottom: 2px solid #475569;
        }}

        .attempts-table td {{
            padding: 12px;
            border-bottom: 1px solid #334155;
            color: #cbd5e1;
        }}

        .attempts-table tr:hover td {{
            background: #252f47;
        }}

        .status-success {{
            color: #2ecc71;
            font-weight: bold;
        }}

        .status-blocked {{
            color: #e74c3c;
            font-weight: bold;
        }}

        /* Screenshot gallery */
        .screenshot-gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 16px;
            margin-top: 16px;
        }}

        .screenshot-card {{
            background: #0f172a;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid #334155;
        }}

        .screenshot-card img {{
            width: 100%;
            height: auto;
            display: block;
        }}

        .screenshot-label {{
            padding: 10px;
            font-size: 0.85em;
            color: #94a3b8;
            text-align: center;
        }}

        /* Footer */
        .footer {{
            text-align: center;
            padding: 30px;
            color: #64748b;
            font-size: 0.85em;
            border-top: 1px solid #334155;
            margin-top: 40px;
        }}

        /* JSON Export */
        .json-export {{
            background: #0f172a;
            border-radius: 8px;
            padding: 16px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
            color: #94a3b8;
            max-height: 400px;
            overflow-y: auto;
        }}

        .btn {{
            display: inline-block;
            padding: 10px 20px;
            background: #3b82f6;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-size: 0.9em;
            margin-top: 10px;
            cursor: pointer;
            border: none;
        }}

        .btn:hover {{
            background: #2563eb;
        }}

        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 1.8em;
            }}
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>Signup Shield Audit Report</h1>
            <p class="subtitle">Automated Security Assessment for Signup Pages</p>
            <p class="timestamp">Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>

        <!-- Score Card -->
        <div class="score-card">
            <div class="score-circle">
                <span class="score-value">{score['overall_percentage']}%</span>
            </div>
            <div class="score-label">SECURITY SCORE: {status_text}</div>
            <div class="score-sublabel">{score['tests_passed']} of {score['total_tests']} security checks passed</div>
        </div>"""

        captcha_solved = signup.get('captcha_solved', 0)
        emails_verified = signup.get('emails_verified', 0)

        # Stats Grid
        html += f"""
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon">🎯</div>
                <div class="stat-value">{meta['num_accounts_executed']}</div>
                <div class="stat-label">Signup Attempts</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">✅</div>
                <div class="stat-value">{signup['successful']}</div>
                <div class="stat-label">Successful Signups</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🛡️</div>
                <div class="stat-value">{signup['blocked']}</div>
                <div class="stat-label">Blocked by Security</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🤖</div>
                <div class="stat-value">{captcha_solved}</div>
                <div class="stat-label">CAPTCHAs Solved</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">📧</div>
                <div class="stat-value">{emails_verified}</div>
                <div class="stat-label">Emails Verified</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">⏱️</div>
                <div class="stat-value">{meta['duration_seconds']}s</div>
                <div class="stat-label">Test Duration</div>
            </div>
        </div>"""

        html += f"""
        <!-- Target Info -->
        <div class="section">
            <div class="section-title">🌐 Target Information</div>
            <div class="test-details">
                <strong>Target URL:</strong> {meta['target_url']}<br>
                <strong>Test Duration:</strong> {meta['duration_seconds']} seconds<br>
                <strong>Tests Performed:</strong><br>
                <ul>
                    <li>CAPTCHA Detection: {'Enabled' if meta['tests_configured']['captcha'] else 'Disabled'}</li>
                    <li>Rate Limiting: {'Enabled' if meta['tests_configured']['rate_limiting'] else 'Disabled'}</li>
                    <li>Email Verification: {'Enabled' if meta['tests_configured']['email_verification'] else 'Disabled'}</li>
                    <li>Password Policy: {'Enabled' if meta['tests_configured']['password_policy'] else 'Disabled'}</li>
                    <li>Duplicate Detection: {'Enabled' if meta['tests_configured']['duplicate_detection'] else 'Disabled'}</li>
                </ul>
            </div>
        </div>"""

        # Security Test Results Section
        html += """
        <div class="section">
            <div class="section-title">🔍 Security Test Results</div>
"""

        # Aggregate results across all attempts
        all_results = []
        for attempt in attempts:
            all_results.extend(attempt.get("security_results", []))

        # Group by test name
        seen_tests = set()
        for result in all_results:
            test_key = result["test_name"]
            if test_key in seen_tests:
                continue
            seen_tests.add(test_key)

            is_pass = result["passed"]
            badge_class = "badge-pass" if is_pass else "badge-fail"
            badge_text = "PASS" if is_pass else "FAIL"
            item_class = "test-pass" if is_pass else "test-fail"

            details_html = ""
            details = result.get("details", {})

            if "status" in details:
                details_html += f"<strong>Status:</strong> {details['status']}<br>"
            if "captcha_type" in details and details["captcha_type"]:
                details_html += f"<strong>CAPTCHA Type:</strong> {details['captcha_type']}<br>"
            if "indicators_found" in details and details["indicators_found"]:
                details_html += "<strong>Indicators Found:</strong><ul>"
                for ind in details["indicators_found"]:
                    details_html += f"<li>{ind}</li>"
                details_html += "</ul>"
            if "html5_validations" in details:
                val = details["html5_validations"]
                details_html += "<strong>HTML5 Validations:</strong><ul>"
                details_html += f"<li>Required: {val.get('required', 'N/A')}</li>"
                details_html += f"<li>Min Length: {val.get('min_length', 'N/A')}</li>"
                details_html += f"<li>Max Length: {val.get('max_length', 'N/A')}</li>"
                details_html += f"<li>Pattern: {val.get('pattern', 'N/A')}</li>"
                details_html += "</ul>"
            if "score" in details:
                details_html += f"<strong>Score:</strong> {details['score']}<br>"
            if "recommendation" in details:
                details_html += f"<strong>Recommendation:</strong> {details['recommendation']}"

            html += f"""
            <div class="test-item {item_class}">
                <div class="test-header">
                    <span class="test-name">{result['test_name']}</span>
                    <span class="test-badge {badge_class}">{badge_text}</span>
                </div>
                <div class="test-details">
                    {details_html}
                </div>
            </div>
"""

        html += "</div>"

        # Recommendations Section
        html += """
        <div class="section">
            <div class="section-title">📋 Recommendations</div>
"""

        for rec in recommendations:
            # Determine severity from prefix
            if rec.startswith("CRITICAL"):
                rec_class = "rec-critical"
            elif rec.startswith("HIGH"):
                rec_class = "rec-high"
            elif rec.startswith("MEDIUM"):
                rec_class = "rec-medium"
            elif rec.startswith("LOW"):
                rec_class = "rec-low"
            elif rec.startswith("Good"):
                rec_class = "rec-good"
            else:
                rec_class = "rec-medium"

            html += f'<div class="recommendation {rec_class}">{rec}</div>'

        html += "</div>"

        # Attempts Table
        html += """
        <div class="section">
            <div class="section-title">📊 Signup Attempts Log</div>
            <table class="attempts-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Location</th>
                        <th>Password</th>
                        <th>Status</th>
                        <th>Message</th>
                    </tr>
                </thead>
                <tbody>
"""

        for attempt in attempts:
            status_class = "status-success" if attempt["success"] else "status-blocked"
            status_text = "SUCCESS" if attempt["success"] else "BLOCKED"
            pw_status = "WEAK" if attempt["identity"].get("is_weak_password") else "Strong"
            pw_color = "#e74c3c" if attempt["identity"].get("is_weak_password") else "#2ecc71"

            html += f"""
                    <tr>
                        <td>{attempt['attempt_number']}</td>
                        <td>{attempt['identity']['name']}</td>
                        <td>{attempt['identity']['email']}</td>
                        <td>{attempt['identity']['location']}</td>
                        <td style="color: {pw_color}">{pw_status}</td>
                        <td class="{status_class}">{status_text}</td>
                        <td>{attempt.get('error_message', 'N/A') or 'N/A'}</td>
                    </tr>
"""

        html += """
                </tbody>
            </table>
        </div>
"""

        # Created Accounts Section
        created = results.get("created_accounts", [])
        if created:
            html += """
        <div class="section">
            <div class="section-title">✅ Created Accounts <span style="font-size:0.7em;color:#94a3b8;font-weight:normal;">(credentials captured)</span></div>
            <table class="attempts-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Password</th>
                        <th>Phone</th>
                        <th>Verified</th>
                    </tr>
                </thead>
                <tbody>
"""
            for idx, acct in enumerate(created):
                verified_badge = '<span style="color:#2ecc71;font-weight:bold;">YES</span>' if acct.get("verified") else '<span style="color:#f39c12;font-weight:bold;">No</span>'
                html += f"""
                    <tr>
                        <td>{acct.get('attempt_number', idx + 1)}</td>
                        <td>{acct.get('name', 'N/A')}</td>
                        <td style="font-family:monospace;font-size:0.85em;">{acct.get('email', 'N/A')}</td>
                        <td style="font-family:monospace;font-size:0.85em;color:#f0b27a;">{acct.get('password', 'N/A')}</td>
                        <td>{acct.get('phone', 'N/A')}</td>
                        <td>{verified_badge}</td>
                    </tr>
"""
            html += """
                </tbody>
            </table>
        </div>
"""

        # Raw Data Export
        html += """
        <div class="section">
            <div class="section-title">📦 Raw Data Export</div>
            <p style="color: #94a3b8; margin-bottom: 12px;">Complete test results in JSON format:</p>
            <div class="json-export">
                <pre>"""
        html += json.dumps(results, indent=2, default=str)
        html += """</pre>
            </div>
        </div>
"""

        # Footer
        html += f"""
        <div class="footer">
            <p>Signup Shield Audit Report</p>
            <p>This report was generated automatically for authorized security testing purposes only.</p>
            <p style="margin-top: 10px; color: #475569;">Target: {meta['target_url']} | Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
    </div>
</body>
</html>
"""

        return html

    def generate_json_report(self, results: Dict) -> str:
        """Generate JSON report file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(self.output_dir, f"security_report_{timestamp}.json")

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(f"JSON report generated: {report_path}")
        return report_path
