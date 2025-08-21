from typing import List, Union

from openai import OpenAI


def get_openai_emb(
    text: Union[str, List[str]],
    api_key: str,
    model: str = "text-embedding-3-small"
) -> Union[List[float], List[List[float]]]:
    """
    Get embedding(s) for one or multiple texts using the specified model.

    Args:
        client (OpenAI): An OpenAI or self-hosted client instance.
        text (str | list[str]): Input text(s) to embed.
        model (str): The embedding model to use (default: text-embedding-3-small).

    Returns:
        list[float] | list[list[float]]: The embedding(s).
    """

    client  = OpenAI(api_key=api_key)


    response = client.embeddings.create(
        input=text,
        model=model,
    )

    # If input was a single string → return a single vector
    if isinstance(text, str):
        return response.data[0].embedding

    # If input was a list → return list of vectors
    return [item.embedding for item in response.data]
