// 夜间模式切换
const darkModeBtn = document.getElementById('toggle-dark-mode');
const body = document.body;

darkModeBtn.addEventListener('click', () => {
    body.classList.toggle('dark-mode');
    const icon = darkModeBtn.querySelector('i');
    if (body.classList.contains('dark-mode')) {
        icon.classList.replace('bi-moon', 'bi-sun');
        darkModeBtn.innerHTML = '<i class="bi bi-sun me-1"></i>日间模式';
    } else {
        icon.classList.replace('bi-sun', 'bi-moon');
        darkModeBtn.innerHTML = '<i class="bi bi-moon me-1"></i>夜间模式';
    }
});

// 动态添加项目
document.getElementById('add-project-btn').addEventListener('click', () => {
    const input = document.getElementById('new-project-input');
    const text = input.value.trim();

    if (!text) {
        alert('请输入项目名称！');
        return;
    }

    const li = document.createElement('li');
    li.className = 'list-group-item';
    li.textContent = text;
    document.getElementById('projects-list').appendChild(li);
    input.value = '';
});

// 滚动动画
window.addEventListener('scroll', () => {
    document.querySelectorAll('.transform-hover').forEach(el => {
        const rect = el.getBoundingClientRect();
        if (rect.top < window.innerHeight && rect.bottom >= 0) {
            el.classList.add('visible');
        }
    });
});

// 初始触发滚动检查
window.dispatchEvent(new Event('scroll'));

// jQuery功能
$(document).ready(() => {
    // 技能项点击隐藏
    $('#skills-list li').click(function() {
        $(this).fadeOut('slow', () => $(this).remove());
    });

    // 个人简介展开/收起
    const bioTitle = $('#bio-title');
    bioTitle.css({ cursor: 'pointer' }).append(' <i class="bi bi-chevron-down"></i>');

    bioTitle.click(function() {
        $('#bio-content').slideToggle('slow');
        $(this).find('i').toggleClass('bi-chevron-down bi-chevron-up');
    });
});
