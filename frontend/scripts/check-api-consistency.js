#!/usr/bin/env node

/**
 * Frontend API Consistency Check Script
 *
 * This script performs basic validation of frontend API calls:
 * 1. Checks for API client imports
 * 2. Validates API call patterns
 * 3. Generates a simple report
 *
 * Note: The main API consistency check is performed by the backend script
 * (backend/scripts/maintenance/api_consistency_check.py), which compares
 * backend endpoints with frontend API calls.
 */

const fs = require('fs');
const path = require('path');
const { glob } = require('glob');

// ANSI color codes for terminal output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  blue: '\x1b[34m',
};

class FrontendAPIConsistencyChecker {
  constructor(frontendPath = '.'):
  {
    this.frontendPath = frontendPath;
    this.issues = [];
  }

  async runChecks() {
    console.log(`${colors.blue}Starting Frontend API Consistency Check...${colors.reset}\n`);

    // Check 1: Find all service files
    const serviceFiles = await this.findServiceFiles();
    console.log(`Found ${serviceFiles.length} service files`);

    // Check 2: Validate API client imports
    this.validateAPIImports(serviceFiles);

    // Check 3: Check API call patterns
    this.validateAPICallPatterns(serviceFiles);

    // Generate report
    this.generateReport();

    // Print summary
    this.printSummary();

    // Return exit code based on issues
    return this.issues.filter(i => i.severity === 'critical').length > 0 ? 1 : 0;
  }

  async findServiceFiles() {
    try {
      const files = await glob('src/services/**/*.ts', {
        cwd: this.frontendPath,
        absolute: false,
      });
      return files.map(f => path.join(this.frontendPath, f));
    } catch (error) {
      console.error(`Error finding service files: ${error.message}`);
      return [];
    }
  }

  validateAPIImports(serviceFiles) {
    console.log(`\n${colors.blue}Checking API client imports...${colors.reset}`);

    for (const file of serviceFiles) {
      try {
        const content = fs.readFileSync(file, 'utf-8');

        // Check if file imports apiClient
        const hasAPIImport = /import.*apiClient.*from\s+['"]@\/api|['"]\.\.\/\.\./.test(content);

        if (!hasAPIImport && content.includes('apiClient')) {
          this.issues.push({
            type: 'import_format',
            severity: 'warning',
            message: `File uses apiClient but has no proper import from @/api: ${path.relative(this.frontendPath, file)}`,
            file: path.relative(this.frontendPath, file),
          });
        }
      } catch (error) {
        this.issues.push({
          type: 'file_read_error',
          severity: 'warning',
          message: `Cannot read file ${file}: ${error.message}`,
          file: path.relative(this.frontendPath, file),
        });
      }
    }
  }

  validateAPICallPatterns(serviceFiles) {
    console.log(`${colors.blue}Checking API call patterns...${colors.reset}`);

    for (const file of serviceFiles) {
      try {
        const content = fs.readFileSync(file, 'utf-8');

        // Check for common API call patterns
        const apiCallPatterns = [
          /apiClient\.(get|post|put|delete|patch)\s*\(/g,
          /enhancedApiClient\.(get|post|put|delete|patch)\s*\(/g,
        ];

        let hasAPICalls = false;
        for (const pattern of apiCallPatterns) {
          if (pattern.test(content)) {
            hasAPICalls = true;
            break;
          }
        }

        if (!hasAPICalls && content.includes('Client')) {
          this.issues.push({
            type: 'no_api_calls',
            severity: 'info',
            message: `Service file has no detectable API calls: ${path.relative(this.frontendPath, file)}`,
            file: path.relative(this.frontendPath, file),
          });
        }
      } catch (error) {
        // Skip files that can't be read
      }
    }
  }

  generateReport() {
    const report = {
      timestamp: new Date().toISOString(),
      total_issues: this.issues.length,
      issues: this.issues.map(issue => ({
        type: issue.type,
        severity: issue.severity,
        message: issue.message,
        file: issue.file,
      })),
    };

    const outputPath = path.join(this.frontendPath, 'frontend-api-consistency-report.json');
    fs.writeFileSync(outputPath, JSON.stringify(report, null, 2));
    console.log(`\n${colors.blue}Report saved to: ${outputPath}${colors.reset}`);
  }

  printSummary() {
    const critical = this.issues.filter(i => i.severity === 'critical');
    const warnings = this.issues.filter(i => i.severity === 'warning');
    const info = this.issues.filter(i => i.severity === 'info');

    console.log(`\n${colors.blue}=== Summary ===${colors.reset}`);
    console.log(`Total Issues: ${this.issues.length}`);
    console.log(`${colors.red}Critical: ${critical.length}${colors.reset}`);
    console.log(`${colors.yellow}Warnings: ${warnings.length}${colors.reset}`);
    console.log(`${colors.blue}Info: ${info.length}${colors.reset}`);

    if (this.issues.length === 0) {
      console.log(`\n${colors.green}✅ All frontend API consistency checks passed!${colors.reset}`);
    } else if (critical.length === 0) {
      console.log(`\n${colors.yellow}⚠️  No critical issues found${colors.reset}`);
    } else {
      console.log(`\n${colors.red}❌ Found ${critical.length} critical issue(s)${colors.reset}`);
      critical.forEach(issue => {
        console.log(`  - ${issue.message}`);
      });
    }
  }
}

// Main execution
(async () => {
  const frontendPath = process.argv[2] || '.';
  const checker = new FrontendAPIConsistencyChecker(frontendPath);
  const exitCode = await checker.runChecks();
  process.exit(exitCode);
})();
