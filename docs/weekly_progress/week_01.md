# Yūgen Mayoiga — Week 1 Progress Report

**Project Title:** Yūgen Mayoiga — A Branching Narrative Story Engine  
**Reporting Period:** Week 1  
**Project Area:** Python, Object-Oriented Programming, Data Structures and Algorithms, Story Logic, and Database Design  
**Status:** Core foundation and initial console prototype implemented

## 1. Week 1 Objectives

The primary objective of Week 1 was to establish the technical foundation of Yūgen Mayoiga. The focus was on organizing the codebase, designing the core story entities, implementing basic story progression, and documenting the system architecture and database structure.

The goal was to create a functional foundation that could later support graph-based narrative exploration, persistent data storage, and a user-facing interface.

## 2. Project Structure and Development Environment

The project repository was organized into separate areas for the application code, algorithms, documentation, tests, and demonstration scripts.

The core story-engine models are located in `backend/app/mayoiga/`, while graph algorithms are maintained separately in `algorithms/`.

This separation improves modularity, makes individual components easier to test, and allows algorithms to evolve without mixing them directly into the core model classes.

## 3. Core Model Implementation

The following Python classes were created to represent the main entities of the story engine.

### 3.1 Character — `character.py`

The `Character` class represents a character whose psychological state can evolve throughout a story.

It stores:
- A unique character identifier.
- The character's name.
- Personality traits.
- Current emotional values.

Traits and emotions are represented using dictionaries, allowing different attributes to be stored and updated flexibly.

The `update_trait()` and `update_emotion()` methods apply numerical changes to these values. The implementation restricts updated values to the range of 0–100 to prevent them from exceeding the intended limits.

**Technical importance:** This provides the foundation for tracking character development and introducing future trait-dependent narrative choices.

### 3.2 Choice — `choice.py`

The `Choice` class represents an action selected by the user during a story.

Each choice stores its identifier, displayed text, destination scene, and optional changes to traits and emotions.

The `apply_to()` method applies the configured changes to a character using the update methods defined in the `Character` class.

**Technical importance:** This separates the definition of a narrative decision from the logic used to apply its effects. It also enables different choices to produce different character-state changes.

### 3.3 Scene — `scene.py`

The `Scene` class represents an individual segment of the narrative.

A scene can contain story content and available choices, allowing the narrative to progress through different paths rather than following only a fixed sequence.

The scene model provides the foundation for connecting narrative content with the graph-based structure of the story engine.

### 3.4 Story — `story.py`

The `Story` class represents a complete narrative.

It organizes scenes, identifies the starting scene, and provides the structure required to retrieve scenes and validate story connections.

**Technical importance:** The story model acts as the container for the narrative, while individual scenes and choices define its internal structure.

### 3.5 StoryState — `story_state.py`

The `StoryState` class tracks the current progress of a story session.

Its responsibilities include:
- Maintaining the current scene identifier.
- Initializing the story at its starting scene.
- Keeping a history of visited scenes.
- Applying a selected choice to the character.
- Moving the story to the destination scene.
- Preventing further choices once an ending scene has been reached.

The class also checks that the story has scenes, defines a starting scene, and references a valid current scene.

**Technical importance:** It connects the story models and character-state updates into a single progression workflow.

## 4. Character Traits and Emotional State

A core design objective is to represent both relatively stable personality attributes and changing emotional states.

For example, a character might have a courage trait of 60 and a fear value of 30. A narrative choice can modify these values independently.

The update methods apply the following boundary rule:

\[
\text{updated value}=\min(100,\max(0,\text{current value}+\text{delta}))
\]

This keeps updated values between 0 and 100.

The implementation supports numerical trait and emotion changes. However, a complete system of predefined trait names, validated values, and conditional choices based on traits remains a potential improvement.

## 5. Initial Console Story Prototype

An initial interactive console demonstration was created in `demo/run_mini_story.py` and run successfully.

The prototype demonstrates the basic workflow of presenting a story, selecting a choice, and progressing through the narrative.

This provides an early functional demonstration of the story engine before the development of a graphical interface or API.

## 6. Architecture and Database Documentation

### 6.1 Architecture Documentation

The project architecture was documented in `docs/architecture.md`.

The document describes the main components and their responsibilities, providing a reference for future implementation and integration.

### 6.2 Database Design

The initial database design was documented in `docs/database_design.md`.

The design describes the proposed data entities, their relationships, and the structure required to represent stories, scenes, choices, characters, and related narrative information.

### 6.3 Entity-Relationship Diagram

The ER diagram documentation was organized under `database/er_diagram/`.

The diagram is intended to make the relationships between database entities easier to understand before the database is implemented.

**Current distinction:** Database design and documentation have been prepared; PostgreSQL integration, ORM models, and database migrations are separate implementation tasks.

## 7. Testing and Verification Status

The initial console prototype was run successfully.

The core model classes contain initial validation and story-progression logic. However, the dedicated unit-test and integration-test files are currently empty.

Therefore, comprehensive automated testing of character updates, invalid choices, scene transitions, and complete story flows remains pending.

## 8. Challenges and Technical Decisions

- **Modularity:** Separate model classes were used to keep character data, narrative choices, scenes, stories, and session progression organized.
- **Flexible character state:** Dictionaries allow traits and emotions to be represented without hardcoding every attribute into the class structure.
- **State boundaries:** Trait and emotion updates are restricted to a defined numerical range.
- **Narrative validation:** Story initialization checks for essential structural requirements before progression begins.
- **Separation of design and implementation:** Database documentation was prepared before the planned database integration stage.

## 9. Week 1 Deliverables

| Deliverable | Status |
|---|---|
| Core Python model classes | Implemented |
| Character trait and emotion update methods | Implemented |
| Choice-based state changes | Implemented |
| Story-state tracking and scene progression | Implemented |
| Initial console story demonstration | Run successfully |
| Architecture documentation | Prepared |
| Database design documentation | Prepared |
| ER diagram documentation | Prepared |
| Automated unit and integration tests | Pending |
| PostgreSQL and ORM integration | Planned |

## 10. Conclusion and Next Steps

Week 1 established the core foundation of Yūgen Mayoiga as a modular, stateful branching narrative engine. The project now has initial models for characters, choices, scenes, stories, and story progression, alongside architecture and database documentation.

The next stage is to strengthen verification through automated tests and extend the graph-based representation of branching narratives. Subsequent development will focus on graph analysis, database integration, backend APIs, and more advanced character-dependent narrative behavior.

The current implementation provides the foundation for these extensions without claiming that the complete application or database layer is already finished.