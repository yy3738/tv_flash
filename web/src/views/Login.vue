<template>
  <el-card class="login-card">
    <template #header>TV Flash 登录</template>
    <el-form @submit.prevent="submit">
      <el-form-item>
        <el-input v-model="username" placeholder="用户名" />
      </el-form-item>
      <el-form-item>
        <el-input v-model="password" type="password" placeholder="密码" show-password />
      </el-form-item>
      <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">
        登录
      </el-button>
      <el-alert v-if="error" :title="error" type="error" :closable="false" style="margin-top: 12px" />
    </el-form>
  </el-card>
</template>

<script setup>
import { ref } from 'vue'
import { login } from '../api'

const emit = defineEmits(['login-success'])
const username = ref('admin')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function submit() {
  loading.value = true
  error.value = ''
  try {
    await login(username.value, password.value)
    emit('login-success')
  } catch (e) {
    error.value = '登录失败：' + e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-card { width: 360px; margin: 80px auto; }
</style>
