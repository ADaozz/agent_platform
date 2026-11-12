<script setup>
import ReviewDisclosure from '../office/ReviewDisclosure.vue'
defineProps({title:String,status:String,statusLabel:String,issues:{type:Array,default:()=>[]},kind:{type:String,default:'visual'}})
</script>
<template><ReviewDisclosure v-bind="$props"><slot /></ReviewDisclosure></template>
