/* ============================================================================
   quiz.js — reusable retrieval-practice widget for the Strategic Programmer
   course. Zero dependencies. Immediate, automatic feedback (tight loop).

   USAGE (in a lesson):
     <div class="quiz" data-quiz></div>
     <script src="../assets/quiz.js"></script>
     <script>
       Quiz.mount({
         mount: '[data-quiz]',
         questions: [
           {
             q: 'Question text (may contain <code>).',
             options: ['Same length A', 'Same length B', 'Same length C'],
             answer: 1,                       // index of correct option
             why: 'Explanation shown after answering (both right and wrong).'
           },
           ...
         ]
       });
     </script>

   DESIGN NOTES
   - Options should be authored to equal word/char length so formatting gives
     no tells. The widget shuffles option order per question to defeat
     position memory (interleaving-friendly).
   - Feedback is retrieval-first: the learner commits before seeing the answer.
   ============================================================================ */
(function (global) {
  'use strict';

  function shuffle(n) {
    var idx = Array.from({ length: n }, function (_, i) { return i; });
    for (var i = idx.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = idx[i]; idx[i] = idx[j]; idx[j] = t;
    }
    return idx;
  }

  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }

  function renderQuestion(container, spec, onDone) {
    var wrap = el('div', 'quiz-q');
    wrap.appendChild(el('div', 'quiz-stem', spec.q));

    var order = shuffle(spec.options.length);
    var answered = false;
    var opts = el('div', 'quiz-opts');

    order.forEach(function (origIdx) {
      var btn = el('button', 'quiz-opt', spec.options[origIdx]);
      btn.type = 'button';
      btn.addEventListener('click', function () {
        if (answered) return;
        answered = true;
        var correct = origIdx === spec.answer;
        Array.prototype.forEach.call(opts.children, function (b, k) {
          b.disabled = true;
          if (order[k] === spec.answer) b.classList.add('is-correct');
        });
        if (!correct) btn.classList.add('is-wrong');
        var fb = el('div', 'quiz-why ' + (correct ? 'ok' : 'no'));
        fb.innerHTML = '<span class="tag">' + (correct ? 'Correct' : 'Not quite') +
          '</span> ' + spec.why;
        wrap.appendChild(fb);
        onDone(correct);
      });
      opts.appendChild(btn);
    });

    wrap.appendChild(opts);
    container.appendChild(wrap);
  }

  var Quiz = {
    mount: function (config) {
      var host = typeof config.mount === 'string'
        ? document.querySelector(config.mount) : config.mount;
      if (!host) return;
      host.classList.add('quiz');

      var head = el('div', 'quiz-head',
        '<span class="quiz-title">Retrieval check</span>' +
        '<span class="quiz-score" data-score>0 / ' + config.questions.length + '</span>');
      host.appendChild(head);

      var scoreEl = head.querySelector('[data-score]');
      var right = 0, done = 0, total = config.questions.length;

      config.questions.forEach(function (spec) {
        renderQuestion(host, spec, function (correct) {
          done++; if (correct) right++;
          scoreEl.textContent = right + ' / ' + total;
          if (done === total) {
            var msg = right === total
              ? 'Clean sweep. Try recalling these cold tomorrow — spacing is what makes it stick.'
              : 'Review the misses, then re-open this lesson in a couple of days and retry from memory.';
            host.appendChild(el('div', 'quiz-done', msg));
          }
        });
      });
    }
  };

  global.Quiz = Quiz;
})(window);
