(function () {
    const chatDialogPlugin = {
      init: function () {
        this.createChatDialog();
        this.addEventListeners();
      },
  
      createChatDialog: function () {
        const chatDialogHTML = `
          <div id="chat-dialog" class="chat-dialog">
            <div class="chat-header">Ask Me</div>
            <div class="chat-body"></div>
            <form class="chat-input-form">
              <input type="text" class="chat-input" placeholder="Type your message..." />
              <button type="submit">Send</button>
            </form>
          </div>
        `;
        document.body.insertAdjacentHTML('beforeend', chatDialogHTML);
      },
  
      addEventListeners: function () {
        const chatInputForm = document.querySelector('.chat-input-form');
        chatInputForm.addEventListener('submit', this.handleSubmit);
      },
  
      handleSubmit: async function (e) {
        e.preventDefault();
        const chatInput = document.querySelector('.chat-input');
        console.log("+++++++chatInput:", chatInput.value);
        let inputMessage = chatInput.value.trim();
        const chatBody = document.querySelector('.chat-body');

        if (inputMessage !== '') {
          const message = document.createElement('div');
          message.classList.add('message');
          message.innerText = inputMessage;
          chatBody.appendChild(message);
          chatInput.value = '';
        }
        
        let ret = await fetch(mkdocs_chat_plugin['docs_chat_endpoint'], {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ message: inputMessage}),
        });
        ret = await ret.json();
        console.log("+++++++ret:", ret);
        console.log("+++++++ret:", ret.received_message);
        const message = document.createElement('div');
        //enable white spaces in div
        message.style.whiteSpace = 'pre-wrap';

        message.classList.add('message');
        message.innerText = ret.received_message;
        chatBody.appendChild(message);
        chatBody.scrollTop = chatBody.scrollHeight;
      },
    };
  
    window.chatDialogPlugin = chatDialogPlugin;
    chatDialogPlugin.init();
})();
