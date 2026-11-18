package org.example.backend.auth.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.extern.slf4j.Slf4j;
import org.example.backend.auth.dto.RegisterDTO;
import org.example.backend.auth.service.RegisterService;
import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.exception.Module;
import org.example.backend.common.utils.PasswordUtils;
import org.example.backend.system.role.entity.SysRoleEntity;
import org.example.backend.system.role.service.SysRoleService;
import org.example.backend.system.user.constant.UserConstants;
import org.example.backend.system.user.entity.SysUserEntity;
import org.example.backend.system.user.service.SysUserRoleService;
import org.example.backend.system.user.service.SysUserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ClassPathResource;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StreamUtils;
import org.springframework.util.StringUtils;

import javax.mail.internet.MimeMessage;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Collections;
import java.util.Date;
import java.util.concurrent.TimeUnit;

@Service
@Slf4j
public class RegisterServiceImpl implements RegisterService {

    private static final String CODE_KEY_PREFIX = "register:code:";
    private static final String INTERVAL_KEY_PREFIX = "register:interval:";
    private static final String ATTEMPTS_KEY_PREFIX = "register:attempts:";
    private static final String MAIL_TEMPLATE = "templates/mail/register-code.html";

    private static final SecureRandom RANDOM = new SecureRandom();

    @Autowired
    private SysUserService sysUserService;

    @Autowired
    private SysUserRoleService sysUserRoleService;

    @Autowired
    private SysRoleService sysRoleService;

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    @Autowired
    private JavaMailSender mailSender;

    @Value("${spring.mail.username:}")
    private String mailFrom;

    /** 验证码有效期，默认 5 分钟 */
    @Value("${register.code.expire-seconds:300}")
    private long expireSeconds;

    /** 同一邮箱重发间隔，默认 60 秒 */
    @Value("${register.code.resend-interval-seconds:60}")
    private long resendIntervalSeconds;

    @Value("${register.code.max-attempts:5}")
    private int maxAttempts;

    /** 注册默认角色名；库中可能是「普通用户」或 user */
    @Value("${register.default-role:普通用户}")
    private String defaultRoleName;

    @Override
    public void sendCode(String email) {
        String normalizedEmail = normalizeEmail(email);
        if (!StringUtils.hasText(mailFrom)) {
            throw new BusinessException(Module.ModuleType.AUTH, "邮件服务未配置，请联系管理员", null);
        }
        if (sysUserService.getByEmail(normalizedEmail) != null) {
            throw new BusinessException(Module.ModuleType.AUTH, "该邮箱已注册", null);
        }

        String intervalKey = INTERVAL_KEY_PREFIX + normalizedEmail;
        if (Boolean.TRUE.equals(stringRedisTemplate.hasKey(intervalKey))) {
            throw new BusinessException(Module.ModuleType.AUTH,
                    "发送过于频繁，请 " + resendIntervalSeconds + " 秒后再试", null);
        }

        String code = String.format("%06d", RANDOM.nextInt(1_000_000));
        long expireMinutes = Math.max(1, expireSeconds / 60);
        try {
            MimeMessage message = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");
            helper.setFrom(mailFrom);
            helper.setTo(normalizedEmail);
            helper.setSubject("Agent Platform 注册验证码");
            helper.setText(buildPlainText(code, expireMinutes), buildHtml(code, expireMinutes));
            mailSender.send(message);
        } catch (BusinessException e) {
            throw e;
        } catch (Exception e) {
            log.error("注册验证码邮件发送失败: email={}", normalizedEmail, e);
            throw new BusinessException(Module.ModuleType.AUTH, "验证码发送失败，请稍后重试", null);
        }

        stringRedisTemplate.opsForValue().set(CODE_KEY_PREFIX + normalizedEmail, code, expireSeconds, TimeUnit.SECONDS);
        stringRedisTemplate.delete(ATTEMPTS_KEY_PREFIX + normalizedEmail);
        stringRedisTemplate.opsForValue().set(intervalKey, "1", resendIntervalSeconds, TimeUnit.SECONDS);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void register(RegisterDTO dto) {
        if (!dto.getPassWord().equals(dto.getConfirmPassWord())) {
            throw new BusinessException(Module.ModuleType.AUTH, "两次输入的密码不一致", null);
        }
        String passwordError = PasswordUtils.validateRegisterPassword(dto.getPassWord());
        if (passwordError != null) {
            throw new BusinessException(Module.ModuleType.AUTH, passwordError, null);
        }

        String userName = dto.getUserName().trim();
        String normalizedEmail = normalizeEmail(dto.getEmail());
        if (sysUserService.getByUserName(userName) != null) {
            throw new BusinessException(Module.ModuleType.AUTH, "用户名已存在", null);
        }
        if (sysUserService.getByEmail(normalizedEmail) != null) {
            throw new BusinessException(Module.ModuleType.AUTH, "该邮箱已注册", null);
        }

        verifyCode(normalizedEmail, dto.getCode());

        Date now = new Date();
        SysUserEntity user = new SysUserEntity();
        user.setUserName(userName);
        user.setEmail(normalizedEmail);
        user.setPassWord(PasswordUtils.encrypt(dto.getPassWord()));
        user.setStatus(UserConstants.STATUS_NORMAL);
        user.setCreateTime(now);
        user.setUpdateTime(now);
        sysUserService.save(user);

        SysRoleEntity defaultRole = getDefaultRole();
        if (defaultRole == null) {
            throw new BusinessException(Module.ModuleType.AUTH, "默认用户角色未配置，请联系管理员", null);
        }
        sysUserRoleService.assignRolesByUserId(user.getUserId(), Collections.singletonList(defaultRole.getRoleId()));

        stringRedisTemplate.delete(CODE_KEY_PREFIX + normalizedEmail);
        stringRedisTemplate.delete(ATTEMPTS_KEY_PREFIX + normalizedEmail);
    }

    private void verifyCode(String email, String code) {
        String codeKey = CODE_KEY_PREFIX + email;
        String cached = stringRedisTemplate.opsForValue().get(codeKey);
        if (!StringUtils.hasText(cached)) {
            throw new BusinessException(Module.ModuleType.AUTH, "验证码不存在或已过期，请重新获取", null);
        }

        boolean matched = MessageDigest.isEqual(
                cached.getBytes(StandardCharsets.UTF_8), code.getBytes(StandardCharsets.UTF_8));
        if (!matched) {
            String attemptsKey = ATTEMPTS_KEY_PREFIX + email;
            Long attempts = stringRedisTemplate.opsForValue().increment(attemptsKey);
            stringRedisTemplate.expire(attemptsKey, expireSeconds, TimeUnit.SECONDS);
            if (attempts != null && attempts >= maxAttempts) {
                stringRedisTemplate.delete(codeKey);
                stringRedisTemplate.delete(attemptsKey);
                throw new BusinessException(Module.ModuleType.AUTH, "验证码错误次数过多，请重新获取", null);
            }
            throw new BusinessException(Module.ModuleType.AUTH, "验证码错误", null);
        }
    }

    private String buildPlainText(String code, long expireMinutes) {
        return "您正在注册 Agent Platform 账号。\n\n"
                + "验证码：" + code + "\n\n"
                + "验证码 " + expireMinutes + " 分钟内有效，请勿泄露给他人。\n"
                + "如非本人操作，请忽略本邮件。\n\n"
                + "— DEEP AGENT / Agent Workspace";
    }

    private String buildHtml(String code, long expireMinutes) {
        try {
            ClassPathResource resource = new ClassPathResource(MAIL_TEMPLATE);
            String html = StreamUtils.copyToString(resource.getInputStream(), StandardCharsets.UTF_8);
            return html
                    .replace("{{CODE}}", code)
                    .replace("{{EXPIRE_MINUTES}}", String.valueOf(expireMinutes));
        } catch (Exception e) {
            log.error("加载注册验证码邮件模板失败", e);
            throw new BusinessException(Module.ModuleType.AUTH, "验证码发送失败，请稍后重试", null);
        }
    }

    private SysRoleEntity getDefaultRole() {
        for (String name : new String[]{defaultRoleName, "普通用户", "user"}) {
            if (!StringUtils.hasText(name)) {
                continue;
            }
            LambdaQueryWrapper<SysRoleEntity> wrapper = new LambdaQueryWrapper<>();
            wrapper.eq(SysRoleEntity::getSysRole, name.trim());
            SysRoleEntity role = sysRoleService.getOne(wrapper);
            if (role != null) {
                return role;
            }
        }
        return sysRoleService.getById(2L);
    }

    private String normalizeEmail(String email) {
        return email == null ? "" : email.trim().toLowerCase();
    }
}
