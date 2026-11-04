
import type {
    MystParsedDirective,
} from "../validation/myst-directive-types";
import type {
    MystLocatedDirective,
    MystLocatedOption,
    MystSourceRange,
} from "./myst-parser-types";

const DIRECTIVE_START =
    /^[ \t]{0,3}(`{3,}|~{3,}|:{3,})[ \t]*\{([\w-]+)\}(?:[ \t]+(.*))?[ \t]*$/;

const CODE_FENCE_START =
    /^[ \t]{0,3}(`{3,}|~{3,})(.*)$/;

const FENCE_END =
    /^[ \t]{0,3}(`{3,}|~{3,}|:{3,})[ \t]*$/;

const OPTION_PATTERN =
    /^[ \t]*:([\w-]+):(?:[ \t]*(.*))?$/;

interface OpenDirective {
    readonly name: string;
    readonly argument: string;
    readonly argumentRange: MystSourceRange;
    readonly startLine: number;
    readonly resultIndex: number;
    readonly options: MystLocatedOption[];
    optionsOpen: boolean;
}

interface OpenFence {
    readonly marker: string;
    readonly directive?: OpenDirective;
}

/**
 * Parses MyST directives while respecting nested fenced blocks.
 */
export class MystDirectiveParser {
    /**
     * Parses directives without source locations.
     *
     * @param content Markdown content.
     * @returns Parsed directives.
     */
    public parse(content: string): MystParsedDirective[] {
        return this.parseWithLocations(content).map(
            ({ name, argument, options }) => ({
                name,
                argument,
                options: options.map(({ name, value }) => ({
                    name,
                    value,
                })),
            }),
        );
    }

    /**
     * Parses directives and their source locations.
     *
     * @param content Markdown content.
     * @returns Located directives in source order.
     */
    public parseWithLocations(
        content: string,
    ): MystLocatedDirective[] {
        const lines = content.split(/\r?\n/);
        const stack: OpenFence[] = [];
        const results: Array<MystLocatedDirective | undefined> = [];

        for (let index = 0; index < lines.length; index++) {
            const line = lines[index];
            const current = stack[stack.length - 1];

            const closing = FENCE_END.exec(line);

            if (
                current &&
                closing &&
                this.matchesClosingFence(
                    current.marker,
                    closing[1],
                )
            ) {
                stack.pop();

                if (current.directive) {
                    const directive = current.directive;

                    results[directive.resultIndex] = {
                        name: directive.name,
                        argument: directive.argument,
                        argumentRange: directive.argumentRange,
                        options: directive.options,
                        range: this.createRange(
                            directive.startLine,
                            0,
                            index,
                            line.length,
                        ),
                    };
                }

                continue;
            }

            // Content inside ordinary code fences is not MyST.
            if (current && !current.directive) {
                continue;
            }

            const directiveMatch = DIRECTIVE_START.exec(line);

            if (directiveMatch) {
                if (current?.directive) {
                    current.directive.optionsOpen = false;
                }

                const marker = directiveMatch[1];
                const argument = (directiveMatch[3] ?? "").trim();

                const argumentStart = argument
                    ? line.indexOf(
                        argument,
                        line.indexOf("}") + 1,
                    )
                    : line.length;

                const directive: OpenDirective = {
                    name: directiveMatch[2],
                    argument,
                    argumentRange: this.createRange(
                        index,
                        argumentStart,
                        index,
                        argumentStart + argument.length,
                    ),
                    startLine: index,
                    resultIndex: results.length,
                    options: [],
                    optionsOpen: true,
                };

                results.push(undefined);

                stack.push({
                    marker,
                    directive,
                });

                continue;
            }

            const codeMatch = CODE_FENCE_START.exec(line);

            if (codeMatch) {
                if (current?.directive) {
                    current.directive.optionsOpen = false;
                }

                stack.push({
                    marker: codeMatch[1],
                });

                continue;
            }

            if (current?.directive && current.directive.optionsOpen) {
                this.collectOption(
                    current.directive,
                    line,
                    index,
                );
            }
        }

        return results.filter(
            (item): item is MystLocatedDirective =>
                item !== undefined,
        );
    }

    /**
     * Checks whether a fence closes the current block.
     *
     * @param opening Opening marker.
     * @param closing Candidate closing marker.
     * @returns Whether the markers match.
     */
    private matchesClosingFence(
        opening: string,
        closing: string,
    ): boolean {
        return (
            opening[0] === closing[0] &&
            closing.length >= opening.length
        );
    }

    /**
     * Collects options from the beginning of a directive body.
     *
     * @param directive Open directive.
     * @param line Current line.
     * @param lineIndex Current line index.
     */
    private collectOption(
        directive: OpenDirective,
        line: string,
        lineIndex: number,
    ): void {
        if (!line.trim() && directive.options.length === 0) {
            return;
        }

        const match = OPTION_PATTERN.exec(line);

        if (!match) {
            directive.optionsOpen = false;
            return;
        }

        directive.options.push({
            name: match[1],
            value: (match[2] ?? "").trim(),
            range: this.createRange(
                lineIndex,
                0,
                lineIndex,
                line.length,
            ),
        });
    }

    /**
     * Creates a zero-based source range.
     *
     * @param startLine Starting line.
     * @param startCharacter Starting character.
     * @param endLine Ending line.
     * @param endCharacter Ending character.
     * @returns Source range.
     */
    private createRange(
        startLine: number,
        startCharacter: number,
        endLine: number,
        endCharacter: number,
    ): MystSourceRange {
        return {
            start: {
                line: startLine,
                character: startCharacter,
            },
            end: {
                line: endLine,
                character: endCharacter,
            },
        };
    }
}
