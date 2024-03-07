document.addEventListener('DOMContentLoaded', function () {
  const apiKey = '77fc7b2fe4dc478c9ef36a45a34acf7a'; // ご自身のAPIキーに置き換えてください
  const searchTerm = 'ランサムウェア OR サイバー攻撃'; // 検索するキーワード

  // ローディングメッセージの表示
  const loadingMessage = document.createElement('p');
  loadingMessage.textContent = 'Loading...';
  document.getElementById('news-container').appendChild(loadingMessage);

  // NewsAPIの`q`パラメータと`excludeDomains`パラメータを使用してキーワード検索
  const apiUrl = `https://newsapi.org/v2/everything?q=${encodeURIComponent(searchTerm)}&excludeDomains=srad.jp,touchlab.jp&apiKey=${apiKey}`;

  fetch(apiUrl)
    .then(response => response.json())
    .then(data => {
      // ローディングメッセージを非表示にする
      loadingMessage.style.display = 'none';

      const newsContainer = document.getElementById('news-container');
      const relevantArticles = data.articles.slice(0, 12); // 最新の15件の記事を取得

      // 記事の更新日でソート（降順）
      relevantArticles.sort((a, b) => new Date(b.publishedAt) - new Date(a.publishedAt));

      relevantArticles.forEach(article => {
        const articleContainer = document.createElement('div');
        articleContainer.classList.add('article-container');

        // 記事の更新日を表示
        if (article.publishedAt) {
          const dateElement = document.createElement('h4');
          dateElement.classList.add('news-date');

          const dateOptions = { year: 'numeric', month: '2-digit', day: '2-digit' };
          const formattedDate = new Date(article.publishedAt).toLocaleDateString('ja-JP', dateOptions);

          dateElement.textContent = `[${formattedDate}]`;
          articleContainer.appendChild(dateElement);
        }


        // 記事タイトルをh3タグで表示
        const titleElement = document.createElement('h3');
        titleElement.classList.add('news-title');

        // 記事タイトルが38文字以上の場合は39文字目以降を省略して表示
        const truncatedTitle = article.title.length > 22 ? article.title.substring(0, 22) + '...' : article.title;
        titleElement.innerHTML = `<a class="article-link" href="${article.url}" target="_blank">${truncatedTitle}</a>`;

        // タイトルを記事コンテナに追加
        articleContainer.appendChild(titleElement);

        newsContainer.appendChild(articleContainer);
        
      });
    })
    .catch(error => console.error('Error fetching news:', error));
});