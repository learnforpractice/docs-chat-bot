from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="docs-chat-bot",
    version="0.0.2",
    description="docs chat bot by leveraging CHATGPT",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="mkdocs plugin",
    url="https://github.com/learnforpractice/docs-chat-bot",
    author="learnforpractice",
    author_email="learnforpractice@gmail.com",
    license="MIT",
    include_package_data=True,
    python_requires=">=3.6",
    classifiers=[
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
    ],
    install_requires=["mkdocs>=1.1", "pymdown-extensions>=9.2"],
    packages=find_packages(),
    # entry_points={
    #     "mkdocs.plugins": ["chat = docs_chat_bot.plugin:ChatPlugin"]
    # },
)
