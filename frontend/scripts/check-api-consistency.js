#!/usr/bin/env node

/**
 * Frontend API Consistency Check Script
 *
 * This script performs basic validation of frontend API calls.
 * Note: The main API consistency check is performed by the backend script.
 */

const fs = require('fs');
const path = require('path');

// ANSI color codes for terminal output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  blue: '\x1b[34m',
};

class FrontendAPIConsistencyChecker {
  constructor(frontendPath) {
    this.frontendPath = frontendPath || '.';
    this.issues = [];
  }

  async runChecks() {
    console.log(colors.blue + 'Starting Frontend API Consistency Check...' + colors.reset + '\n');

    // Find all service files
    const serviceFiles = this.findServiceFiles();
    console.log('Found ' + serviceFiles.length + ' service files');

    // Validate API client imports
    this.validateAPIImports(serviceFiles);

    // Generate report
    this.generateReport();

    // Print summary
    this.printSummary();

    // Return exit code
    return this.issues.filter(i => i.severity === 'critical').length > 0 ? 1 : 0;
  }

  findServiceFiles() {
    const files = [];
    const servicesDir = path.join(this.frontendPath, 'src/services');

    if (fs.existsSync(servicesDir)) {
      const entries = fs.readdirSync(servicesDir, { withFileTypes: true });
      for (const entry of entries) {
        if (entry.isFile() && entry.name.endsWith('.ts')) {
          files.push(path.join(servicesDir, entry.name));
        }
      }
    }

    return files;
  }

  validateAPIImports(serviceFiles) {
    console.log('\n' + colors.blue + 'Checking API client imports...' + colors.reset);

    for (const file of serviceFiles) {
      try {
        const content = fs.readFileSync(file, 'utf-8');

        // Check if file imports apiClient
        const hasAPIImport = /import.*apiClient.*from\s+['"]@\/api|['"]\.\.\/\.\./.test(content);

        if (!hasAPIImport && content.includes('apiClient')) {
          this.issues.push({
            type: 'import_format',
            severity: 'warning',
            message:
              'File uses apiClient but has no proper import from @/api: ' +
              path.relative(this.frontendPath, file),
            file: path.relative(this.frontendPath, file),
          });
        }
      } catch (error) {
        this.issues.push({
          type: 'file_read_error',
          severity: 'warning',
          message: 'Cannot read file ' + file + ': ' + error.message,
          file: path.relative(this.frontendPath, file),
        });
      }
    }
  }

  generateReport() {
    const report = {
      timestamp: new Date().toISOString(),
      total_issues: this.issues.length,
      issues: this.issues.map(function (issue) {
        return {
          type: issue.type,
          severity: issue.severity,
          message: issue.message,
          file: issue.file,
        };
      }),
    };

    const outputPath = path.join(this.frontendPath, 'frontend-api-consistency-report.json');
    fs.writeFileSync(outputPath, JSON.stringify(report, null, 2));
    console.log('\n' + colors.blue + 'Report saved to: ' + outputPath + colors.reset);
  }

  printSummary() {
    const critical = this.issues.filter(function (i) {
      return i.severity === 'critical';
    });
    const warnings = this.issues.filter(function (i) {
      return i.severity === 'warning';
    });
    const info = this.issues.filter(function (i) {
      return i.severity === 'info';
    });

    console.log('\n' + colors.blue + '=== Summary ===' + colors.reset);
    console.log('Total Issues: ' + this.issues.length);
    console.log(colors.red + 'Critical: ' + critical.length + colors.reset);
    console.log(colors.yellow + 'Warnings: ' + warnings.length + colors.reset);
    console.log(colors.blue + 'Info: ' + info.length + colors.reset);

    if (this.issues.length === 0) {
      console.log(
        '\n' + colors.green + '✅ All frontend API consistency checks passed!' + colors.reset
      );
    } else if (critical.length === 0) {
      console.log('\n' + colors.yellow + '⚠️  No critical issues found' + colors.reset);
    }
  }
}

// Main execution
(function () {
  const frontendPath = process.argv[2] || '.';
  const checker = new FrontendAPIConsistencyChecker(frontendPath);

  checker
    .runChecks()
    .then(function (exitCode) {
      process.exit(exitCode);
    })
    .catch(function (error) {
      console.error('Error running checks:', error.message);
      process.exit(1);
    });
})();
