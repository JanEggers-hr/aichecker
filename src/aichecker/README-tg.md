# Telegram-Posts lesen


Von Channeln kann man Posts auf zwei Arten lesen: 

- über ihre Kontextseite (t.me/s/<channel>/<id>)
- über ihre individuelle Post-Seite (t.me/s/<channel>/<id>)

# Kontextseite


Die Kontextseite ist etwas bequemer, denn: 
- sie lädt direkt komplett (die Post-Seite lädt ein Embed nach)
- sie wird auch angezeigt, wenn es die Post-ID nicht gibt


# Postseite


Die Postseite lädt die eigentlichen Inhalte als Embed in ein iframe. Es ist möglich, dieses Embed direkt über requests zu laden: 
- https://t.me/<channel>/<id>?embed=1&mode=tme
  - Parameter embed: alles >0 scheint zu funktionieren
  - Parameter mode: akzeptiert auch andere Namen
- Untersuchen, ob es ein Element div.tgme_widget_message_error enthält - dann konnte der Post nicht geladen werden
- Enthält ein Element div.tgme_widget_message_error

<div class="tgme_widget_message text_not_supported_wrap js-widget_message" data-post="telegram/361" data-view="eyJjIjotMTAwNTY0MDg5MiwicCI6MzYxLCJ0IjoxNzM1OTQxNTY5LCJoIjoiOGJmNWMzZDM1OTE0Y2I1NTMyIn0" data-peer="c1005640892_-6044378432856379164" data-peer-hash="556f33b85ddb50a1e1" data-post-id="361">