# SWP DB Schema Format Guide

## Overview

This document outlines the formatting conventions and structure of the `swpdb.json` schema file used within the APE (Agentic Pipeline Engine). The schema defines the database structure for the Software Development Portal (SWP) system and is designed to be easily understood by both humans and Large Language Models (LLMs).

## Key Format Principles

1. **Pure JSON**: The schema is stored in pure JSON format (no markdown wrappers) for maximum compatibility with tools, LLMs, and agent systems.

2. **Multilingual Support**: All descriptive text includes both English (`en`) and Korean (`ko`) versions to support internationalization.

3. **Hierarchical Organization**: The schema follows a clear hierarchical structure to represent database elements.

4. **Rich Metadata**: Includes explicit metadata to help LLMs better understand and reason about the schema.

## Schema Structure

The schema follows this high-level structure:

```
{
  "name": "swdpdb",                        // Schema identifier
  "description": { multilingual object },  // General description
  "parameters": { ... },                   // Query parameters
  "reasoning_strategy": { ... },           // Guidance for reasoning
  "database_schema": {                     // Core schema definition
    "database_name": "SWDP",
    "database_type": "MySQL 5.7",
    "tables": [ ... ],                     // Table definitions
    "relationships": [ ... ],              // Inter-table relationships
    "codes": { ... }                       // Enumeration codes
  },
  "common_queries": [ ... ],               // Example query templates
  "metadata": { ... }                      // LLM processing hints
}
```

## LLM-Friendly Features

The schema includes several features specifically designed to enhance LLM understanding:

1. **Explicit Relationships**: All table relationships are explicitly defined in the `relationships` section rather than being implicit.

2. **Processing Hints**: The `metadata.llm_processing_hints` section provides direct guidance to LLMs on how to understand and use the schema.

3. **Common Operations**: Frequently used queries are provided as templates with explanations.

4. **Type Information**: All fields include explicit type information to avoid ambiguity.

## Agent Compatibility

This schema format is designed to be compatible with:

1. **RAG Agents**: For retrieval-augmented generation with database queries
2. **SQL Generation Agents**: For translating natural language to SQL
3. **LangGraph Agents**: For workflow-based database interactions
4. **Data Analysis Agents**: For summarizing and analyzing database contents

## Best Practices for Schema Updates

When updating the schema:

1. Maintain the existing structure
2. Preserve multilingual descriptions
3. Add explicit relationships for any new tables
4. Update common queries to reflect schema changes
5. Update metadata if the fundamental structure changes

## Versioning

The schema includes version information in the metadata section. When making significant changes, update this version number following semantic versioning principles (MAJOR.MINOR.PATCH).