client."""

    @tool
    async def get_single_file(
        repository_url: str,
        branch: str,
        file_path: str,
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        """Read a file from the repository. Text is returned as text,
        images are loaded into the conversation so you can look at them.

        Args:
            repository_url: Repository URL.
            branch: Branch name, e.g. 'release/D-5.4.2'.
            file_path: Path to the file inside the repository.

        Returns:
            Command updating the message history with file content.
        """
        owner, repo = parse_repository_url(repository_url)
        status, raw = await client.get_file_raw(owner, repo, file_path, branch)

        def _reply(text: str) -> Command:
            """Wrap a plain-text answer into a state update."""
            return Command(
                update={"messages": [ToolMessage(text, tool_call_id=tool_call_id)]}
            )

        if status != 200:
            return _reply(f"[ERROR {status}: {file_path}]")

        try:
            return _reply(raw.decode("utf-8"))
        except UnicodeDecodeError:
            pass  # не текст — проверяем, картинка ли это

        if Path(file_path).suffix.lower() not in IMAGE_EXTENSIONS:
            return _reply(f"[BINARY: {file_path}, {len(raw)} bytes, not a text file]")

        if len(raw) > MAX_IMAGE_BYTES:
            return _reply(f"[IMAGE too large: {file_path}, {len(raw)} bytes]")

        mime = mimetypes.guess_type(file_path)[0] or "image/jpeg"
        encoded = base64.b64encode(raw).decode("ascii")
        logger.info(f"Image loaded into context: {file_path} ({len(raw)} bytes)")

        # ToolMessage — только текст (ограничение схемы).
        # Сама картинка идёт следующим HumanMessage: только роль `user`
        # может нести image content block.
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        f"Image {file_path} loaded — see the next message.",
                        tool_call_id=tool_call_id,
                    ),
                    HumanMessage(
                        content=[
                            {
                                "type": "text",
                                "text": f"Изображение из файла {file_path}:",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime};base64,{encoded}"
                                },
                            },
                        ]
                    ),
                ]
            }
        )