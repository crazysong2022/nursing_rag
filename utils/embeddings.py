from sentence_transformers import SentenceTransformer

class EmbeddingGenerator:
    """
    A class used to generate embeddings for text data using Sentence Transformers.
    """

    def __init__(self, model_name='paraphrase-MiniLM-L6-v2'):
        """
        Initialize the embedding generator with a specified Sentence Transformers model.
        
        :param model_name: The name of the Sentence Transformers model to use.
        """
        # Load the Sentence Transformers model
        self.model = SentenceTransformer(model_name)

    def generate_embeddings(self, texts):
        """
        Generate embeddings for a list of text strings.
        
        :param texts: A list of text strings to generate embeddings for.
        :return: A list of embeddings, where each embedding is a numpy array.
        """
        # Generate embeddings using the Sentence Transformers model
        embeddings = self.model.encode(texts)
        return embeddings