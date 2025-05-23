"""
Docusaurus formatter agent for AutoDoc AI.

This agent generates Docusaurus-compatible documentation from analyzed code,
creating well-structured Markdown files ready for building into a website.
"""

import os
import re
import json
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from autodocai.agents.base import BaseAgent
from autodocai.schemas import CodeSnippet, MessageType


class DocusaurusFormatterAgent(BaseAgent):
    """Agent for formatting documentation in Docusaurus format.
    
    This agent takes the analyzed code, summaries, diagrams, and other content
    and formats them into a well-structured Docusaurus-compatible documentation.
    """
    
    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the documentation formatting process.
        
        Args:
            state: Current workflow state
            
        Returns:
            Dict[str, Any]: Updated workflow state with documentation path
        """
        # Get necessary data from state
        repo_info = state.get("repo_info")
        if not repo_info:
            raise ValueError("Repository information is missing")
        
        snippets = state.get("snippets", [])
        summaries = state.get("summaries", {})
        diagrams = state.get("diagrams", {})
        rag_results = state.get("rag_results", {})
        
        # Create output directory
        output_dir = self.config.output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Create documentation structure
        docs_dir = os.path.join(output_dir, "docs")
        if os.path.exists(docs_dir):
            shutil.rmtree(docs_dir)
        os.makedirs(docs_dir)
        
        self.logger.info(f"Starting documentation generation in {docs_dir}")
        self._add_message(state, MessageType.INFO, f"Starting documentation generation")
        
        # Create necessary directories for i18n if Vietnamese is requested
        i18n_vi_dir = None
        if "VI" in self.config.output_languages:
            i18n_dir = os.path.join(output_dir, "i18n")
            i18n_vi_dir = os.path.join(i18n_dir, "vi", "docusaurus-plugin-content-docs", "current")
            os.makedirs(i18n_vi_dir, exist_ok=True)
        
        # Generate documentation files
        try:
            # Create basic Docusaurus configuration
            await self._create_docusaurus_config(output_dir, repo_info.name)
            
            # Create homepage
            await self._create_homepage(output_dir, repo_info, rag_results)
            
            # Create introduction page
            intro_path = await self._create_introduction(docs_dir, repo_info, rag_results)
            if i18n_vi_dir and intro_path:
                await self._create_introduction(i18n_vi_dir, repo_info, rag_results, language="vi")
            
            # Create architecture page with diagrams
            if diagrams:
                arch_path = await self._create_architecture_page(docs_dir, diagrams, rag_results)
                if i18n_vi_dir and arch_path:
                    await self._create_architecture_page(i18n_vi_dir, diagrams, rag_results, language="vi")
            
            # Group snippets by module/file
            module_snippets = self._group_snippets_by_module(snippets)
            
            # Create module pages
            for module_path, module_data in module_snippets.items():
                await self._create_module_page(
                    docs_dir, module_path, module_data["snippets"], 
                    summaries, diagrams, rag_results
                )
                
                if i18n_vi_dir:
                    await self._create_module_page(
                        i18n_vi_dir, module_path, module_data["snippets"], 
                        summaries, diagrams, rag_results, language="vi"
                    )
            
            # Create sidebar configuration
            await self._create_sidebar_config(docs_dir, module_snippets.keys())
            
            self.logger.info(f"Documentation generated successfully in {output_dir}")
            self._add_message(
                state, 
                MessageType.SUCCESS, 
                f"Documentation generated successfully"
            )
            
            # Add docs path to state
            state["docs_path"] = output_dir
            
            return state
            
        except Exception as e:
            self.logger.error(f"Error generating documentation: {str(e)}")
            raise ValueError(f"Failed to generate documentation: {str(e)}")
    
    async def _create_docusaurus_config(self, output_dir: str, project_name: str):
        """Create Docusaurus configuration files.
        
        Args:
            output_dir: Output directory
            project_name: Name of the project
        """
        # Create docusaurus.config.js
        config_path = os.path.join(output_dir, "docusaurus.config.js")
        
        config_content = f"""// @ts-check
// Note: type annotations allow type checking and IDEs autocompletion

const lightCodeTheme = require('prism-react-renderer/themes/github');
const darkCodeTheme = require('prism-react-renderer/themes/dracula');

/** @type {{import('@docusaurus/types').Config}} */
const config = {{
  title: '{project_name} Documentation',
  tagline: 'Generated by AutoDoc AI',
  favicon: 'img/favicon.ico',

  // Set the production url of your site here
  url: 'https://your-docusaurus-site.example.com',
  // Set the /<baseUrl>/ pathname under which your site is served
  // For GitHub pages deployment, it is often '/<projectName>/'
  baseUrl: '/',

  // GitHub pages deployment config.
  // If you aren't using GitHub pages, you don't need these.
  organizationName: 'your-org', // Usually your GitHub org/user name.
  projectName: '{project_name}', // Usually your repo name.

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  // Even if you don't use internalization, you can use this field to set useful
  // metadata like html lang. For example, if your site is Chinese, you may want
  // to replace "en" with "zh-Hans".
  i18n: {{
    defaultLocale: 'en',
    locales: ['en', 'vi'],
  }},

  presets: [
    [
      'classic',
      /** @type {{import('@docusaurus/preset-classic').Options}} */
      ({{
        docs: {{
          sidebarPath: require.resolve('./sidebars.js'),
          // Please change this to your repo.
          // Remove this to remove the "edit this page" links.
          // editUrl: 'https://github.com/your-org/{project_name}/tree/main/docs/',
        }},
        theme: {{
          customCss: require.resolve('./src/css/custom.css'),
        }},
      }}),
    ],
  ],

  themes: ['@docusaurus/theme-mermaid'],
  markdown: {{
    mermaid: true,
  }},

  themeConfig:
    /** @type {{import('@docusaurus/preset-classic').ThemeConfig}} */
    ({{
      // Replace with your project's social card
      image: 'img/docusaurus-social-card.jpg',
      navbar: {{
        title: '{project_name} Documentation',
        logo: {{
          alt: '{project_name} Logo',
          src: 'img/logo.svg',
        }},
        items: [
          {{
            type: 'docSidebar',
            sidebarId: 'tutorialSidebar',
            position: 'left',
            label: 'Documentation',
          }},
          {{
            type: 'localeDropdown',
            position: 'right',
          }},
          {{
            href: 'https://github.com/your-org/{project_name}',
            label: 'GitHub',
            position: 'right',
          }},
        ],
      }},
      footer: {{
        style: 'dark',
        links: [
          {{
            title: 'Documentation',
            items: [
              {{
                label: 'Introduction',
                to: '/docs/intro',
              }},
            ],
          }},
          {{
            title: 'Community',
            items: [
              {{
                label: 'GitHub',
                href: 'https://github.com/your-org/{project_name}',
              }},
            ],
          }},
        ],
        copyright: `Copyright © ${{new Date().getFullYear()}} | Documentation generated by AutoDoc AI.`,
      }},
      prism: {{
        theme: lightCodeTheme,
        darkTheme: darkCodeTheme,
        additionalLanguages: ['python', 'java', 'javascript', 'typescript', 'bash'],
      }},
    }}),
}};

module.exports = config;
"""
        
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        # Create sidebars.js
        sidebars_path = os.path.join(output_dir, "sidebars.js")
        
        sidebars_content = """/** @type {{import('@docusaurus/plugin-content-docs').SidebarsConfig}} */
const sidebars = {
  tutorialSidebar: [
    {
      type: 'category',
      label: 'Documentation',
      items: [
        'intro',
        'architecture',
        {
          type: 'category',
          label: 'Modules',
          items: [
            // Module items will be added dynamically
          ],
        },
      ],
    },
  ],
};

module.exports = sidebars;
"""
        
        with open(sidebars_path, 'w') as f:
            f.write(sidebars_content)
        
        # Create minimal CSS
        src_css_dir = os.path.join(output_dir, "src", "css")
        os.makedirs(src_css_dir, exist_ok=True)
        
        css_path = os.path.join(src_css_dir, "custom.css")
        
        css_content = """/**
 * Any CSS included here will be global. The classic template
 * bundles Infima by default. Infima is a CSS framework designed to
 * work well for content-centric websites.
 */

/* You can override the default Infima variables here. */
:root {
  --ifm-color-primary: #2e8555;
  --ifm-color-primary-dark: #29784c;
  --ifm-color-primary-darker: #277148;
  --ifm-color-primary-darkest: #205d3b;
  --ifm-color-primary-light: #33925d;
  --ifm-color-primary-lighter: #359962;
  --ifm-color-primary-lightest: #3cad6e;
  --ifm-code-font-size: 95%;
  --docusaurus-highlighted-code-line-bg: rgba(0, 0, 0, 0.1);
}

/* For readability concerns, you should choose a lighter palette in dark mode. */
[data-theme='dark'] {
  --ifm-color-primary: #25c2a0;
  --ifm-color-primary-dark: #21af90;
  --ifm-color-primary-darker: #1fa588;
  --ifm-color-primary-darkest: #1a8870;
  --ifm-color-primary-light: #29d5b0;
  --ifm-color-primary-lighter: #32d8b4;
  --ifm-color-primary-lightest: #4fddbf;
  --docusaurus-highlighted-code-line-bg: rgba(0, 0, 0, 0.3);
}
"""
        
        with open(css_path, 'w') as f:
            f.write(css_content)
        
        # Create static directories and placeholder logo
        static_img_dir = os.path.join(output_dir, "static", "img")
        os.makedirs(static_img_dir, exist_ok=True)
        
        # Create a simple SVG logo placeholder
        logo_path = os.path.join(static_img_dir, "logo.svg")
        
        logo_content = """<svg width="200" height="200" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
  <rect width="200" height="200" fill="#2e8555" rx="10" ry="10"/>
  <text x="50%" y="50%" font-size="36" text-anchor="middle" fill="white" font-family="Arial" dominant-baseline="middle">AutoDoc</text>
</svg>
"""
        
        with open(logo_path, 'w') as f:
            f.write(logo_content)
