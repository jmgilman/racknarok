/**
 * Pulumi ESC Sync Project
 *
 * Syncs configuration and secrets from Git to Pulumi ESC environments.
 * Reads config/esc-mapping.yaml to determine which files map to which environments,
 * then creates/updates ESC environments accordingly.
 */

import * as pulumi from '@pulumi/pulumi';
import * as service from '@pulumi/pulumiservice';
import * as yaml from 'js-yaml';
import * as path from 'path';
import { loadEscMapping, loadEnvironmentData } from './lib/loader';
import { isSopsAvailable } from './lib/sops';

// Repository root is two levels up from this file (pulumi/esc-sync -> root)
const repoRoot = path.resolve(__dirname, '../..');
const org = 'jmgilman';
const project = 'racknarok';

// Verify SOPS is available
if (!isSopsAvailable()) {
    throw new Error('SOPS not found in PATH. Please ensure SOPS is installed.');
}

console.log(`Repository root: ${repoRoot}`);
console.log(`Loading ESC mapping from: ${path.join(repoRoot, 'config/esc-mapping.yaml')}`);

// Load the ESC mapping configuration
const mapping = loadEscMapping(repoRoot);
const environments: service.Environment[] = [];

// Create/update an ESC environment for each entry in the mapping
for (const [envName, envConfig] of Object.entries(mapping.environments)) {
    console.log(`\n=== Processing environment: ${envName} ===`);

    // Load and merge config and secrets
    const data = loadEnvironmentData(envName, mapping, repoRoot);

    console.log(`Loaded ${Object.keys(data).length} top-level keys`);

    // Create the ESC environment YAML structure
    // pulumiConfig must be nested under 'values' per Pulumi ESC documentation
    // Keys are accessible to Pulumi programs without project prefix (use pulumi.Config(''))
    // or with explicit prefix like 'proxmox:vms' if needed by specific projects
    const escYaml = {
        values: {
            pulumiConfig: data,  // Nest all data under values.pulumiConfig
        },
    };

    // Convert to YAML string
    const yamlString = yaml.dump(escYaml, {
        indent: 2,
        lineWidth: -1, // Don't wrap lines
        noRefs: true, // Don't use YAML references
    });

    // Create the Environment resource
    const environment = new service.Environment(envName, {
        organization: org,
        project: project,
        name: envName,
        yaml: new pulumi.asset.StringAsset(yamlString),
    });

    environments.push(environment);
}

// Export stack outputs
export const organizationName = org;
export const projectName = project;
export const environmentNames = Object.keys(mapping.environments);
export const environmentCount = Object.keys(mapping.environments).length;

// Export all environment revisions as a single object
export const environmentRevisions = environments.reduce((acc, env, i) => {
    const envName = Object.keys(mapping.environments)[i];
    acc[envName] = env.revision;
    return acc;
}, {} as Record<string, pulumi.Output<number>>);
